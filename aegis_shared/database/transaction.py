from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .manager import DatabaseManager


class TransactionManager:
    """트랜잭션 관리자"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """트랜잭션 컨텍스트 매니저"""
        # Use DatabaseManager's existing session management
        async with self.db_manager.get_session() as session:
            yield session


def transactional(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Assuming the service has a db_manager attribute
        db_manager: DatabaseManager = self.db_manager
        async with db_manager.session():
            # You might want to pass the session to the function
            # if it needs it, e.g., by adding a `session` argument to it.
            return await func(self, *args, **kwargs)

    return wrapper
