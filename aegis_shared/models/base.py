"""
기본 모델 클래스

모든 엔티티가 상속받는 기본 모델을 제공합니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID, uuid4

class BaseEntity(BaseModel):
    """모든 엔티티의 기본 모델"""
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class PaginatedResponse(BaseModel):
    """페이지네이션 응답"""
    
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: List[Any], total: int, page: int, page_size: int):
        """
        페이지네이션 응답 생성
        
        Args:
            items: 아이템 목록
            total: 전체 아이템 수
            page: 현재 페이지
            page_size: 페이지 크기
            
        Returns:
            PaginatedResponse 인스턴스
        """
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )