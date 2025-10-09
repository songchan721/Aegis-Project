"""
기본 모델 클래스

모든 엔티티가 상속받는 기본 모델을 제공합니다.
"""

from datetime import UTC, datetime
from typing import Any, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class BaseEntity(BaseModel):
    """모든 엔티티의 기본 모델"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at", "deleted_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    @field_serializer("id", when_used="json")
    def serialize_uuid(self, u: UUID) -> str:
        return str(u)


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
            total_pages=(total + page_size - 1) // page_size,
        )
