class DatabaseError(Exception):
    """Base exception for database related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.message = message
        self.error_code = self.__class__.__name__
        self.details = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class ConnectionError(DatabaseError):
    """Raised when a connection to the database fails."""


class NoResultFound(DatabaseError):
    """Raised when a query returns no result."""


class MultipleResultsFound(DatabaseError):
    """Raised when a query returns multiple results but expected one."""


class DatabaseConnectionError(DatabaseError):
    """데이터베이스 연결 오류"""


class EntityNotFoundError(DatabaseError):
    """엔티티를 찾을 수 없는 오류"""


class DuplicateEntityError(DatabaseError):
    """중복 엔티티 오류"""
