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

class AdminUserCreate(UserCreate):
    active: bool = True

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

class AdminResetPasswordRequest(BaseModel):
    password: str

class LicenseCreate(BaseModel):
    user_id: str
    plan: str
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    seats: int = 1
    status: str = "active"
    notes: str = ""

class LicenseUpdate(BaseModel):
    plan: Optional[str] = None
    status: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    seats: Optional[int] = None
    notes: Optional[str] = None

class LicenseOut(BaseModel):
    id: str
    user_id: str
    username: str
    email: str
    plan: str
    status: str
    effective_status: str
    seats: int
    notes: str
    starts_at: datetime
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    days_remaining: int

class LicenseCheckOut(BaseModel):
    has_valid_license: bool
    is_admin: bool
    status: str
    plan: Optional[str] = None
    expires_at: Optional[datetime] = None
    days_remaining: int = 0
    message: str

class LicenseRequestOut(BaseModel):
    id: str
    user_id: str
    username: str
    email: str
    status: str
    reason: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
