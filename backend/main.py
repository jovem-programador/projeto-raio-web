import os, uuid, shutil
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import redis

from database import get_db, User
from auth import hash_password, verify_password, create_token, get_current_user, require_admin
from models import TokenResponse, UserCreate, UserOut, JobStatus
from worker.tasks import processar_dwg

from starlette.datastructures import UploadFile as StarletteUploadFile
import starlette.formparsers as fp

# Configurações
UPLOAD_DIR  = Path(os.getenv("UPLOAD_DIR",  "storage/uploads"))
RESULT_DIR  = Path(os.getenv("RESULT_DIR",  "storage/results"))
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ODA_PATH    = os.getenv("ODA_PATH", r"C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Projeto Raio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # ajustar para IP do servidor em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aumenta o limite de upload para 500MB
fp.MAX_FILE_SIZE = 500 * 1024 * 1024      # 500MB por arquivo
fp.MAX_FIELDS    = 1000
fp.MAX_FILES     = 200

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# ── AUTH ──────────────────────────────────────────────────────
@app.post("/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username, User.active == True).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, username=user.username)

# ── ADMIN: GESTÃO DE USUÁRIOS ──────────────────────────────────
@app.get("/admin/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(User).all()

@app.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Usuário já existe")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

@app.patch("/admin/users/{user_id}/toggle")
def toggle_user(user_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.active = not user.active
    db.commit()
    return {"id": user_id, "active": user.active}

@app.delete("/admin/users/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user); db.commit()

# ── Logica de criação de usuário ──
@app.post("/auth/register", response_model=UserOut)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Verifica se o usuário ou email já existem
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuário ou Email já cadastrado")

    # Cria o novo usuário inativo por padrão
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role="operador", # Força sempre operador no autocadastro
        active=False     # AGUARDANDO APROVAÇÃO
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# ── CRIAR ADMIN INICIAL (chamar uma vez) ──────────────────────
@app.post("/setup/admin", include_in_schema=False)
def setup_admin(db: Session = Depends(get_db)):
    if db.query(User).filter(User.role == "admin").first():
        raise HTTPException(status_code=409, detail="Admin já existe")
    user = User(
        username="anderson.marley",
        email="anderson.marley@projetacs.com",
        hashed_password=hash_password("Lima@9299"),
        role="admin",
    )
    db.add(user); db.commit()
    return {"msg": "Admin criado. Altere a senha imediatamente."}

# ── PROCESSAMENTO ──────────────────────────────────────────────
MAX_FILE_SIZE_MB = 100

@app.post("/jobs/upload")
async def upload(
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user)
):
    job_id   = str(uuid.uuid4())
    job_dir  = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True)

    saved = []
    for f in files:
        # valida extensão
        if not f.filename.lower().endswith(".dwg"):
            raise HTTPException(status_code=400, detail=f"Arquivo inválido: {f.filename}")
        # valida tamanho (lê em chunks)
        dest = job_dir / f.filename
        total = 0
        with open(dest, "wb") as out:
            while chunk := await f.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_FILE_SIZE_MB * 1024 * 1024:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"{f.filename} excede {MAX_FILE_SIZE_MB}MB")
                out.write(chunk)
        saved.append(str(dest))

    # inicializa status no Redis
    redis_client.hset(f"job:{job_id}", mapping={
        "status": "queued",
        "total_files": len(saved),
        "processed": 0,
        "user": user.username,
    })

    # dispara task assíncrona
    processar_dwg.delay(job_id, saved, str(RESULT_DIR), ODA_PATH)

    return {"job_id": job_id, "total_files": len(saved)}


@app.get("/jobs/{job_id}/status", response_model=JobStatus)
def job_status(job_id: str, user=Depends(get_current_user)):
    data = redis_client.hgetall(f"job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    # operadores só veem seus próprios jobs
    if user.role != "admin" and data.get("user") != user.username:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return JobStatus(
        job_id=job_id,
        status=data.get("status", "unknown"),
        total_files=int(data.get("total_files", 0)),
        processed=int(data.get("processed", 0)),
        error_msg=data.get("error_msg"),
        download_ready=data.get("status") == "done",
    )


@app.get("/jobs/{job_id}/download")
def download_results(job_id: str, token: str = Query(...), db: Session = Depends(get_db)):
    # 1. Valida o usuário pelo token (importante para segurança)
    user = get_current_user(token, db)
    
    # 2. Busca os dados do job no Redis
    job_data = redis_client.hgetall(f"job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    # 3. Verifica se o processamento terminou e se o caminho do arquivo existe
    result_path = job_data.get("result_path")
    if job_data.get("status") != "done" or not result_path:
        raise HTTPException(status_code=400, detail="Arquivo ainda não disponível")

    # 4. RETORNA O ARQUIVO REAL (O "Pulo do Gato")
    return FileResponse(
        path=result_path, 
        filename=f"Extracao_{job_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ── LISTAR JOBS (admin vê todos, operador vê só os seus) ───────
@app.get("/jobs")
def list_jobs(user=Depends(get_current_user)):
    keys = redis_client.keys("job:*")
    jobs = []
    for key in keys:
        data = redis_client.hgetall(key)
        if user.role != "admin" and data.get("user") != user.username:
            continue
        job_id = key.split(":")[1]
        jobs.append({
            "job_id": job_id,
            "status": data.get("status"),
            "total_files": int(data.get("total_files", 0)),
            "processed": int(data.get("processed", 0)),
            "user": data.get("user"),
            "download_ready": data.get("status") == "done",
        })
    return sorted(jobs, key=lambda x: x["job_id"], reverse=True)