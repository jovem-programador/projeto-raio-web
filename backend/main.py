import os, uuid, shutil, io, zipfile, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import redis
from database import get_db, User, License, LicenseRequest
from auth import hash_password, verify_password, create_token, get_current_user, require_admin
from models import TokenResponse, UserCreate, UserOut, JobStatus, ResetPasswordRequest, LicenseCreate, LicenseUpdate, LicenseOut, LicenseCheckOut, LicenseRequestOut
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

def _active_license_for_user(db: Session, user: User):
    now = datetime.utcnow()
    return (
        db.query(License)
        .filter(
            License.user_id == user.id,
            License.status == "active",
            License.expires_at >= now,
        )
        .order_by(License.expires_at.desc())
        .first()
    )

def _license_check_payload(db: Session, user: User) -> dict:
    if user.role == "admin":
        return {
            "has_valid_license": True,
            "is_admin": True,
            "status": "admin_exempt",
            "plan": None,
            "expires_at": None,
            "days_remaining": 0,
            "message": "Administradores não precisam de licença para operar o sistema.",
        }

    active_license = _active_license_for_user(db, user)
    if active_license:
        days_remaining = max((active_license.expires_at - datetime.utcnow()).days, 0)
        return {
            "has_valid_license": True,
            "is_admin": False,
            "status": "active",
            "plan": active_license.plan,
            "expires_at": active_license.expires_at,
            "days_remaining": days_remaining,
            "message": "Licença ativa.",
        }

    latest_license = (
        db.query(License)
        .filter(License.user_id == user.id)
        .order_by(License.expires_at.desc())
        .first()
    )
    status_msg = "missing"
    message = "Você ainda não possui uma licença ativa para processar arquivos."

    if latest_license:
        if latest_license.status == "suspended":
            status_msg = "suspended"
            message = "Sua licença está suspensa. Procure um administrador."
        elif latest_license.status == "canceled":
            status_msg = "canceled"
            message = "Sua licença foi cancelada. Procure um administrador."
        elif latest_license.expires_at < datetime.utcnow():
            status_msg = "expired"
            message = "Sua licença expirou. Procure um administrador para renovação."

    return {
        "has_valid_license": False,
        "is_admin": False,
        "status": status_msg,
        "plan": latest_license.plan if latest_license else None,
        "expires_at": latest_license.expires_at if latest_license else None,
        "days_remaining": 0,
        "message": message,
    }

def require_valid_license(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.role == "admin" or _active_license_for_user(db, user):
        return user

    payload = _license_check_payload(db, user)
    raise HTTPException(status_code=403, detail=payload["message"])

@app.get("/license/me", response_model=LicenseCheckOut)
def get_my_license_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _license_check_payload(db, user)

@app.post("/license/request-admin")
def request_license_admin_contact(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = _license_check_payload(db, user)
    if payload["has_valid_license"]:
        return {"detail": "Sua licença já está ativa."}

    existing = (
        db.query(LicenseRequest)
        .filter(LicenseRequest.user_id == user.id, LicenseRequest.status == "open")
        .first()
    )
    if existing:
        return {"detail": "Sua solicitação já está aguardando análise do administrador."}

    request = LicenseRequest(
        user_id=user.id,
        status="open",
        reason=payload["status"],
    )
    db.add(request)
    db.commit()

    return {"detail": "Solicitação enviada ao painel do administrador."}

@app.post("/jobs/upload")
async def upload(files: list[UploadFile] = File(...), user=Depends(require_valid_license)):
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

@app.patch("/admin/users/{user_id}/promote")
def promote_user_to_admin(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Promove um usuário existente ao perfil de administrador.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.role == "admin":
        return {"detail": f"Usuário {user.username} já é administrador"}

    user.role = "admin"
    db.commit()

    return {"detail": f"Usuário {user.username} promovido a administrador com sucesso"}

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

# ── CONTROLE DE LICENÇAS (ADMIN) ───────────────────────────────

LICENSE_DURATIONS = {
    "mensal": 30,
    "trimestral": 90,
    "anual": 365,
}

LICENSE_STATUSES = {"active", "suspended", "canceled"}

def _normalize_license_plan(plan: str) -> str:
    normalized = (plan or "").strip().lower()
    if normalized not in LICENSE_DURATIONS:
        raise HTTPException(status_code=400, detail="Plano inválido. Use mensal, trimestral ou anual.")
    return normalized

def _normalize_license_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized not in LICENSE_STATUSES:
        raise HTTPException(status_code=400, detail="Status inválido. Use active, suspended ou canceled.")
    return normalized

def _license_expires_at(starts_at: datetime, plan: str) -> datetime:
    return starts_at + timedelta(days=LICENSE_DURATIONS[plan])

def _license_to_out(license: License, user: User) -> dict:
    now = datetime.utcnow()
    days_remaining = (license.expires_at - now).days
    effective_status = license.status
    if license.status == "active" and license.expires_at < now:
        effective_status = "expired"

    return {
        "id": license.id,
        "user_id": license.user_id,
        "username": user.username if user else "Usuário removido",
        "email": user.email if user else "",
        "plan": license.plan,
        "status": license.status,
        "effective_status": effective_status,
        "seats": license.seats,
        "notes": license.notes or "",
        "starts_at": license.starts_at,
        "expires_at": license.expires_at,
        "created_at": license.created_at,
        "updated_at": license.updated_at,
        "days_remaining": max(days_remaining, 0),
    }

def _license_request_to_out(request: LicenseRequest, user: User) -> dict:
    return {
        "id": request.id,
        "user_id": request.user_id,
        "username": user.username if user else "Usuário removido",
        "email": user.email if user else "",
        "status": request.status,
        "reason": request.reason or "",
        "created_at": request.created_at,
        "resolved_at": request.resolved_at,
    }

@app.get("/admin/license-requests", response_model=list[LicenseRequestOut])
def list_license_requests(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    requests = db.query(LicenseRequest).order_by(LicenseRequest.created_at.desc()).all()
    users_by_id = {u.id: u for u in db.query(User).all()}
    return [_license_request_to_out(request, users_by_id.get(request.user_id)) for request in requests]

@app.patch("/admin/license-requests/{request_id}/resolve")
def resolve_license_request(request_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    request = db.query(LicenseRequest).filter(LicenseRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    request.status = "resolved"
    request.resolved_at = datetime.utcnow()
    db.commit()
    return {"detail": "Solicitação marcada como resolvida"}

@app.get("/admin/licenses", response_model=list[LicenseOut])
def list_licenses(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    licenses = db.query(License).all()
    users_by_id = {u.id: u for u in db.query(User).all()}
    return sorted(
        [_license_to_out(license, users_by_id.get(license.user_id)) for license in licenses],
        key=lambda item: (item["effective_status"] != "active", item["expires_at"]),
    )

@app.post("/admin/licenses", response_model=LicenseOut)
def create_license(data: LicenseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    plan = _normalize_license_plan(data.plan)
    status = _normalize_license_status(data.status)
    starts_at = data.starts_at or datetime.utcnow()
    expires_at = data.expires_at or _license_expires_at(starts_at, plan)
    seats = max(data.seats, 1)

    license = License(
        user_id=user.id,
        plan=plan,
        status=status,
        starts_at=starts_at,
        expires_at=expires_at,
        seats=seats,
        notes=(data.notes or "").strip(),
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    return _license_to_out(license, user)

@app.patch("/admin/licenses/{license_id}", response_model=LicenseOut)
def update_license(license_id: str, data: LicenseUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    if data.plan is not None:
        license.plan = _normalize_license_plan(data.plan)
        if data.expires_at is None:
            license.expires_at = _license_expires_at(data.starts_at or license.starts_at, license.plan)

    if data.status is not None:
        license.status = _normalize_license_status(data.status)
    if data.starts_at is not None:
        license.starts_at = data.starts_at
        if data.expires_at is None:
            license.expires_at = _license_expires_at(license.starts_at, license.plan)
    if data.expires_at is not None:
        license.expires_at = data.expires_at
    if data.seats is not None:
        license.seats = max(data.seats, 1)
    if data.notes is not None:
        license.notes = data.notes.strip()

    license.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(license)

    user = db.query(User).filter(User.id == license.user_id).first()
    return _license_to_out(license, user)

@app.post("/admin/licenses/{license_id}/renew", response_model=LicenseOut)
def renew_license(license_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    base_date = max(license.expires_at, datetime.utcnow())
    license.starts_at = base_date
    license.expires_at = _license_expires_at(base_date, license.plan)
    license.status = "active"
    license.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(license)

    user = db.query(User).filter(User.id == license.user_id).first()
    return _license_to_out(license, user)

@app.delete("/admin/licenses/{license_id}")
def delete_license(license_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    db.delete(license)
    db.commit()
    return {"detail": "Licença removida com sucesso"}

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
