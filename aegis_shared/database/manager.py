from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

class DatabaseManager:
    def __init__(self, database_url: str, **engine_kwargs):
        self.engine = create_async_engine(database_url, **engine_kwargs)
        self.async_session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    async def session(self) -> AsyncSession:
        """Alias for get_session for backward compatibility."""
        async with self.get_session() as session:
            yield session

    async def close(self):
        await self.engine.dispose()
