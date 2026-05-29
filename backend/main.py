import os, uuid, shutil, io, zipfile, re
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import redis
from database import get_db, User
from auth import hash_password, verify_password, create_token, get_current_user, require_admin
from models import TokenResponse, UserCreate, UserOut, JobStatus, ResetPasswordRequest
from worker.tasks import processar_dwg
import urllib.parse
from fastapi.security import OAuth2PasswordRequestForm

# Configurações de Ambiente
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

# Conexão Redis (decode_responses=True para facilitar manipulação de strings)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# ── AUTH ──────────────────────────────────────────────────────
@app.post("/auth/register", response_model=UserOut)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role="operador",
        active=False # Requer aprovação do admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not user.active:
        raise HTTPException(status_code=403, detail="Sua conta aguarda aprovação do administrador.")

    access_token = create_token({"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }

# ── JOBS / EXTRAÇÃO ───────────────────────────────────────────

@app.post("/jobs/upload")
async def upload(files: list[UploadFile] = File(...), user=Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    allowed_exts = {".dwg", ".pdf"}
    filenames = []
    ignored = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_exts:
            ignored.append(file.filename)
            continue
        file_path = job_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        filenames.append(file.filename)

    if not filenames:
        raise HTTPException(
            status_code=400,
            detail="Nenhum ficheiro válido enviado. Formatos suportados: .dwg e .pdf",
        )

    # Guarda no Redis com a string de nomes separada por vírgula
    redis_client.hset(f"job:{job_id}", mapping={
        "status": "queued",
        "total_files": len(filenames),
        "processed": 0,
        "user": user.username,
        "filenames": ",".join(filenames),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    processar_dwg.delay(job_id)
    return {"job_id": job_id, "total_files": len(filenames), "ignored": ignored}

@app.get("/jobs")
def list_jobs(user=Depends(get_current_user)):
    keys = redis_client.keys("job:*")
    jobs = []

    for key in keys:
        data = redis_client.hgetall(key)
        if not data:
            continue

        if user.role != "admin" and data.get("user") != user.username:
            continue

        job_id = key.split(":")[1]
        raw_names = data.get("filenames", "")
        filenames_list = raw_names.split(",") if raw_names else []

        if not data.get("status"):
            continue

        jobs.append({
            "job_id": job_id,
            "status": data.get("status"),
            "total_files": int(data.get("total_files", 0)),
            "processed": int(data.get("processed", 0)),
            "user": data.get("user"),
            "download_ready": data.get("status") == "done",
            "filenames": filenames_list,
            "created_at": data.get("created_at"),
            "started_at": data.get("started_at"),
            "finished_at": data.get("finished_at"),
        })

    return sorted(
        jobs,
        key=lambda x: (x.get("created_at") or "", x["job_id"]),
        reverse=True,
    )

@app.delete("/jobs/clear")
def clear_jobs(current_user: User = Depends(get_current_user)):
    try:
        keys = redis_client.keys("job:*")
        deleted_count = 0

        for key in keys:
            data = redis_client.hgetall(key)
            owner = data.get("user")
            can_delete = (
                current_user.role == "admin"
                or owner == current_user.username
                or not owner  # limpa registros órfãos/legados sem dono
            )
            if can_delete:
                job_id = key.split(":")[1]
                # Marca como removido para impedir que o worker recrie o item após o clear.
                redis_client.set(f"job_deleted:{job_id}", "1", ex=60 * 60 * 24)
                redis_client.delete(key)
                deleted_count += 1

        return {"detail": f"Histórico limpo: {deleted_count} registros removidos."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar: {str(e)}")

@app.get("/jobs/{job_id}/download")
def download_result(job_id: str, user=Depends(get_current_user)):
    data = redis_client.hgetall(f"job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    # Validação de segurança
    if user.role != "admin" and data.get("user") != user.username:
        raise HTTPException(status_code=403, detail="Acesso negado")

    result_path = RESULT_DIR / f"{job_id}.xlsx"
    
    if not result_path.exists():
        # Se o arquivo não existir, o FastAPI retornará 404 em JSON. 
        # Com a função de Blob acima, o 'catch' do frontend vai avisar o usuário.
        raise HTTPException(status_code=404, detail="O arquivo Excel ainda não foi gerado.")

    return FileResponse(
        path=result_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Extracao_Raio.xlsx"
    )


@app.post("/tools/rename-files")
async def rename_files(
    base_name: str = Form(""),
    search_text: str = Form(""),
    replace_text: str = Form(""),
    caderno_tecnico: bool = Form(False),
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    base_name = (base_name or "").strip()

    # Sanitiza para nome de arquivo seguro no Windows.
    safe_base = re.sub(r'[<>:"/\\|?*]+', "_", base_name).strip().strip(".")
    safe_base = re.sub(r"\s+", "_", safe_base)
    # Regra padrão solicitada para nome-base: trocar "-" por "_".
    safe_base = safe_base.replace("-", "_")
    search_text = (search_text or "").strip()
    replace_text = (replace_text or "").strip().replace("-", "_")
    if safe_base and search_text:
        safe_base = safe_base.replace(search_text, replace_text)

    allowed_exts = {".dwg", ".pdf"}
    valid_files = [f for f in files if Path(f.filename or "").suffix.lower() in allowed_exts]
    if not valid_files:
        raise HTTPException(
            status_code=400,
            detail="Nenhum ficheiro válido enviado. Formatos suportados: .dwg e .pdf",
        )

    zip_buffer = io.BytesIO()
    used_names: set[str] = set()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for idx, upload in enumerate(valid_files, start=1):
            original_name = upload.filename or f"arquivo_{idx}"
            original_stem = Path(original_name).stem
            ext = Path(original_name).suffix.lower()
            # Se base_name estiver vazio, respeita o nome original (aplicando apenas pesquisar/substituir).
            target_stem = safe_base if safe_base else original_stem
            if search_text:
                target_stem = target_stem.replace(search_text, replace_text)

            # Segurança mínima para nomes inválidos no Windows.
            target_stem = re.sub(r'[<>:"/\\|?*]+', "_", target_stem).strip().strip(".")
            target_stem = target_stem if target_stem else f"arquivo_{idx}"

            if caderno_tecnico:
                new_name = f"{target_stem}_Fl{idx:04d}{ext}"
            else:
                new_name = f"{target_stem}{ext}"

            # Evita sobrescrever entradas com mesmo nome dentro do ZIP.
            if new_name in used_names:
                dup = 2
                base_candidate = target_stem
                while f"{base_candidate}_dup{dup}{ext}" in used_names:
                    dup += 1
                new_name = f"{base_candidate}_dup{dup}{ext}"

            used_names.add(new_name)
            content = await upload.read()
            zipf.writestr(new_name, content)

    zip_buffer.seek(0)
    output_name = f"{safe_base}_renomeados.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{output_name}"'},
    )

# ── GERENCIAMENTO DE USUÁRIOS (ADMIN) ──────────────────────────

@app.get("/admin/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Retorna a lista de todos os usuários cadastrados.
    Apenas acessível por administradores.
    """
    return db.query(User).all()

@app.patch("/admin/users/{user_id}/toggle")
def toggle_user_status(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Ativa ou desativa um usuário (Aprovação de conta).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Alterna o status active
    user.active = not user.active
    db.commit()
    
    status = "ativado" if user.active else "desativado"
    return {"detail": f"Usuário {user.username} {status} com sucesso"}

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Exclui permanentemente um usuário.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db.delete(user)
    db.commit()
    return {"detail": "Usuário removido com sucesso"}

@app.post("/auth/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == data.identifier) | (User.email == data.identifier)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.hashed_password = hash_password(data.password)
    db.commit()

    return {"detail": "Senha atualizada com sucesso"}
