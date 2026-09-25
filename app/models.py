from app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(225), unique=True, nullable=False)
    password_hash = Column(String(225), nullable=False)
    full_name = Column(String(225), unique=True,  nullable=False)
    role = Column(String(50), nullable=False, default='SYSTEM_ADMIN')
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    