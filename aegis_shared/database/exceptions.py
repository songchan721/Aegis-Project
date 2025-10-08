class DatabaseError(Exception):
    """Base exception for database related errors."""
    pass

class ConnectionError(DatabaseError):
    """Raised when a connection to the database fails."""
    pass

class NoResultFound(DatabaseError):
    """Raised when a query returns no result."""
    pass

class MultipleResultsFound(DatabaseError):
    """Raised when a query returns multiple results but expected one."""
    pass

class DatabaseConnectionError(DatabaseError):
    """데이터베이스 연결 오류"""
    pass

class EntityNotFoundError(DatabaseError):
    """엔티티를 찾을 수 없는 오류"""
    pass

class DuplicateEntityError(DatabaseError):
    """중복 엔티티 오류"""
    pass
