"""
Aegis Shared Library - 데이터베이스 모듈

데이터베이스 연결 관리 및 Repository 패턴을 제공합니다.
"""

from aegis_shared.database.base_repository import BaseRepository
from aegis_shared.database.connection import DatabaseManager
from aegis_shared.database.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
    MultipleResultsFound,
    NoResultFound,
)
from aegis_shared.database.retry import db_retry, with_db_retry
from aegis_shared.database.transaction import TransactionManager, transactional

__all__ = [
    "DatabaseManager",
    "BaseRepository",
    "TransactionManager",
    "transactional",
    "with_db_retry",
    "db_retry",
    "DatabaseError",
    "DatabaseConnectionError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "NoResultFound",
    "MultipleResultsFound",
]
