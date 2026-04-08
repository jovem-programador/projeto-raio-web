from sqlalchemy import create_engine, Column, String, Boolean, DateTime
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

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()