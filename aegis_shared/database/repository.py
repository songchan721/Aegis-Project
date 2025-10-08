from typing import Generic, TypeVar, Type, List, Optional, Union, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, data) -> T:
        if isinstance(data, self.model):
            # Already a SQLAlchemy model instance
            instance = data
        elif hasattr(data, 'dict') and callable(getattr(data, 'dict')):
            # Pydantic model
            instance = self.model(**data.dict())
        elif isinstance(data, dict):
            # Dictionary
            instance = self.model(**data)
        else:
            # Try to convert to dict if it has attributes
            if hasattr(data, '__dict__'):
                # Convert object attributes to dict, excluding private attributes
                data_dict = {key: value for key, value in data.__dict__.items() if not key.startswith('_')}
                instance = self.model(**data_dict)
            else:
                # Assume it's already a SQLAlchemy model instance
                instance = data
        
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get(self, id: UUID) -> Optional[T]:
        return await self.session.get(self.model, id)
    
    async def get_by_id(self, id: Union[UUID, int]) -> Optional[T]:
        """Alias for get method for backward compatibility."""
        return await self.session.get(self.model, id)
    
    async def get_by_ids(self, ids: List[Union[UUID, int]]) -> List[T]:
        """Get multiple entities by their IDs."""
        result = await self.session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return result.scalars().all()

    async def update(self, id: Union[UUID, int], data=None, **kwargs) -> Optional[T]:
        # Handle both dictionary data and keyword arguments
        if data is not None:
            if hasattr(data, 'dict'):
                # Pydantic model
                update_data = data.dict(exclude_unset=True)
            elif isinstance(data, dict):
                # Dictionary
                update_data = data
            else:
                # Convert object to dict (for SQLAlchemy models)
                update_data = {key: value for key, value in data.__dict__.items() if not key.startswith('_')}
        else:
            # Use keyword arguments
            update_data = kwargs
        
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**update_data)
        )
        return await self.get(id)

    async def delete(self, id: Union[UUID, int], soft: bool = False) -> bool:
        if soft and hasattr(self.model, 'deleted_at'):
            # Soft delete by setting deleted_at timestamp
            from datetime import datetime
            result = await self.session.execute(
                update(self.model).where(self.model.id == id).values(deleted_at=datetime.utcnow())
            )
            return result.rowcount > 0
        else:
            # Hard delete
            result = await self.session.execute(delete(self.model).where(self.model.id == id))
            return result.rowcount > 0

    async def soft_delete(self, id: Union[UUID, int]) -> Optional[T]:
        """Soft delete an entity by setting deleted_at timestamp."""
        if hasattr(self.model, 'deleted_at'):
            from datetime import datetime
            await self.session.execute(
                update(self.model).where(self.model.id == id).values(deleted_at=datetime.utcnow())
            )
            return await self.get(id)
        else:
            raise AttributeError(f"Model {self.model.__name__} does not support soft delete (no deleted_at field)")

    async def list(
        self, skip: int = 0, limit: int = 100, filters: Optional[dict] = None
    ) -> List[T]:
        query = select(self.model)
        if filters:
            query = query.filter_by(**filters)
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all()
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count entities with optional filters."""
        from sqlalchemy import func
        query = select(func.count(self.model.id))
        if filters:
            query = query.filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self, id: Union[UUID, int]) -> bool:
        """Check if an entity exists by ID."""
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.first() is not None
