import os, uuid, shutil
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import redis
from pydantic import BaseModel

from database import get_db, User
from auth import hash_password, verify_password, create_token, get_current_user, require_admin
from models import TokenResponse, UserCreate, UserOut, JobStatus
from worker.tasks import processar_dwg
import urllib.parse

# --- SCHEMAS PARA VALIDAÇÃO ---
class LoginSchema(BaseModel):
    username: str
    password: str

# --- CONFIGURAÇÕES DE AMBIENTE ---
UPLOAD_DIR  = Path(os.getenv("UPLOAD_DIR",  "storage/uploads"))
RESULT_DIR  = Path(os.getenv("RESULT_DIR",  "storage/results"))
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Projeto Raio API", version="1.0.0")

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# --- ROTAS DE AUTENTICAÇÃO ---

@app.post("/auth/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    # Verifica se já existe usuário ou email
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Nome de usuário já existe")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        active=False  # Requer aprovação do admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    # Busca por username OU email
    user = db.query(User).filter(
        (User.username == data.username) | (User.email == data.username)
    ).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not user.active:
        raise HTTPException(status_code=403, detail="Sua conta aguarda aprovação do administrador")
    
    token = create_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "role": user.role, 
        "username": user.username
    }

@app.post("/auth/reset-password")
def reset_password(identifier: str, new_password: str, db: Session = Depends(get_db)):
    # Localiza o usuário pelo username ou email
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não localizado")
    
    # Atualiza com HASH (essencial para o login funcionar depois)
    user.hashed_password = hash_password(new_password)
    db.commit()
    
    return {"detail": "Senha atualizada com sucesso"}

@app.post("/setup/admin", include_in_schema=False)
def setup_admin(db: Session = Depends(get_db)):
    if db.query(User).filter(User.role == "admin").first():
        raise HTTPException(status_code=409, detail="Admin já existe")
    
    user = User(
        username="admin",
        email="admin@projeta.com",
        hashed_password=hash_password("TroqueEstaSenh@123"),
        role="admin",
        active=True,   # ← admin precisa estar ativo desde o início
    )
    db.add(user)
    db.commit()
    return {"msg": "Admin criado. Acesse com usuário 'admin' e altere a senha."}

# --- ROTAS DE PROCESSAMENTO (DWG) ---

@app.post("/jobs/upload")
async def upload_dwgs(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    job_id = str(uuid.uuid4())
    total = len(files)
    
    # Pasta temporária para este job
    job_path = UPLOAD_DIR / job_id
    job_path.mkdir()

    for file in files:
        file_path = job_path / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # Regista o estado inicial no Redis
    redis_client.hset(f"job:{job_id}", mapping={
        "status": "queued",
        "total_files": total,
        "processed": 0,
        "download_ready": "false"
    })

    # Dispara tarefa para o Celery
    processar_dwg.delay(job_id, str(job_path))

    return {"job_id": job_id, "message": f"{total} arquivos recebidos"}

@app.get("/jobs/{job_id}/status", response_model=JobStatus)
def get_status(job_id: str):
    data = redis_client.hgetall(f"job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return JobStatus(
        job_id=job_id,
        status=data["status"],
        total_files=int(data["total_files"]),
        processed=int(data["processed"]),
        error_msg=data.get("error_msg"),
        download_ready=(data["download_ready"] == "true")
    )

@app.get("/jobs/{job_id}/download")
def download_result(job_id: str):
    result_file = RESULT_DIR / f"resultado_{job_id}.xlsx"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="Arquivo não disponível")
    
    return FileResponse(
        path=result_file, 
        filename=f"extracao_{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- ROTAS DE ADMINISTRAÇÃO ---

@app.get("/admin/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return db.query(User).all()

@app.post("/admin/users/{user_id}/toggle")
def toggle_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.active = not user.active
    db.commit()
    return {"detail": f"Status de {user.username} alterado para {'ativo' if user.active else 'inativo'}"}

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db.delete(user)
    db.commit()
    return {"detail": "Usuário removido com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.delete("/jobs")
def clear_jobs(current_user: User = Depends(get_current_user)):
    try:
        # 1. Busca todas as chaves de jobs no Redis
        keys = redis_client.keys("job:*")
        if keys:
            redis_client.delete(*keys)
        
        # 2. Opcional: Limpar pastas físicas (CUIDADO: isso apaga os arquivos)
        # shutil.rmtree(UPLOAD_DIR)
        # UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        return {"detail": "Histórico removido com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
def list_all_jobs(current_user: User = Depends(get_current_user)):
    keys = redis_client.keys("job:*")
    jobs = []
    for key in keys:
        job_data = redis_client.hgetall(key)
        job_id = key.split(":")[1]
        jobs.append({
            "job_id": job_id,
            "status": job_data.get("status"),
            "total_files": int(job_data.get("total_files", 0)),
            "processed": int(job_data.get("processed", 0)),
            "download_ready": job_data.get("download_ready") == "true"
        })
    return jobs