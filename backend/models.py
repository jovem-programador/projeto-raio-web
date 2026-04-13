from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "operador"

class UserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class JobStatus(BaseModel):
    job_id: str
    status: str          # queued | processing | done | error
    total_files: int = 0
    processed: int = 0
    error_msg: Optional[str] = None
    download_ready: bool = False

class ResetPasswordRequest(BaseModel):
    identifier: str
    password: str