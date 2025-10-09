"""
Base Repository 패턴

모든 Repository가 상속받는 기본 CRUD 기능을 제공합니다.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

T = TypeVar("T", bound=DeclarativeMeta)


class BaseRepository(Generic[T]):
    """
    모든 Repository가 상속받는 기본 클래스

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)
    """

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        """
        Repository 초기화

        Args:
            session: SQLAlchemy 비동기 세션
            model_class: 모델 클래스
        """
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, id: Any) -> Optional[T]:
        """ID로 단일 엔티티 조회"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[Any]) -> List[T]:
        """여러 ID로 엔티티 조회"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id.in_(ids))
        )
        return list(result.scalars().all())

    async def create(self, entity: T) -> T:
        """엔티티 생성"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_many(self, entities: List[T]) -> List[T]:
        """여러 엔티티 생성"""
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def update(self, id: Any, **kwargs) -> Optional[T]:
        """엔티티 업데이트"""
        await self.session.execute(
            update(self.model_class).where(self.model_class.id == id).values(**kwargs)
        )
        return await self.get_by_id(id)

    async def delete(self, id: Any) -> bool:
        """엔티티 삭제"""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == id)
        )
        return result.rowcount > 0

    async def soft_delete(self, id: Any) -> Optional[T]:
        """소프트 삭제 (deleted_at 설정)"""
        from datetime import UTC, datetime

        return await self.update(id, deleted_at=datetime.now(UTC))

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
    ) -> List[T]:
        """엔티티 목록 조회"""
        query = select(self.model_class)

        # 필터 적용
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)

        # 정렬
        if order_by and hasattr(self.model_class, order_by):
            query = query.order_by(getattr(self.model_class, order_by))

        # 페이지네이션
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """엔티티 개수 조회"""
        query = select(func.count()).select_from(self.model_class)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)

        result = await self.session.execute(query)
        return result.scalar()

    async def exists(self, id: Any) -> bool:
        """엔티티 존재 여부 확인"""
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.id == id)
        )
        return result.scalar() > 0
