"""
샘플 서비스 데이터 모델

Aegis Shared Library의 BaseEntity를 사용한 모델 정의 예시
"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from aegis_shared.models import BaseEntity

# SQLAlchemy 모델
Base = declarative_base()

class User(Base):
    """사용자 데이터베이스 모델"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

# Pydantic 모델 (API 계약)

class UserBase(BaseModel):
    """사용자 기본 모델"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    """사용자 생성 모델"""
    pass

class UserUpdate(BaseModel):
    """사용자 업데이트 모델"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None

class UserResponse(BaseEntity):
    """사용자 응답 모델"""
    email: str
    name: str
    is_active: bool
    
    class Config:
        from_attributes = True

class UserAnalytics(BaseModel):
    """사용자 분석 데이터 모델"""
    user_id: str
    login_count: int
    last_login: Optional[datetime] = None
    activity_score: float = Field(..., ge=0, le=100)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

# 이벤트 스키마 (메시징용)

class UserCreatedEvent(BaseModel):
    """사용자 생성 이벤트"""
    user_id: str
    email: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserUpdatedEvent(BaseModel):
    """사용자 업데이트 이벤트"""
    user_id: str
    changes: dict
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserDeletedEvent(BaseModel):
    """사용자 삭제 이벤트"""
    user_id: str
    deleted_at: datetime = Field(default_factory=datetime.utcnow)