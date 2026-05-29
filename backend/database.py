from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
import uuid

engine = create_engine("sqlite:///./raio.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id       = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email    = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role     = Column(String, default="operador")   # "admin" ou "operador"
    active   = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class License(Base):
    __tablename__ = "licenses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    plan = Column(String, nullable=False)      # mensal, trimestral ou anual
    status = Column(String, default="active")  # active, suspended ou canceled
    seats = Column(Integer, default=1)
    notes = Column(String, default="")
    starts_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class LicenseRequest(Base):
    __tablename__ = "license_requests"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    status = Column(String, default="open")  # open ou resolved
    reason = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
