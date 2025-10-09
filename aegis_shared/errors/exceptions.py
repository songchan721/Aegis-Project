from typing import Dict, Any, Optional
from datetime import datetime, UTC

class ErrorCode:
    """중앙 에러 코드 레지스트리"""

    # 공통 에러 (1000-1999)
    UNKNOWN_ERROR = "COMMON_1000"
    VALIDATION_ERROR = "COMMON_1001"
    AUTHENTICATION_ERROR = "COMMON_1002"
    AUTHORIZATION_ERROR = "COMMON_1003"
    NOT_FOUND_ERROR = "COMMON_1004"
    DUPLICATE_ERROR = "COMMON_1005"
    EXTERNAL_SERVICE_ERROR = "COMMON_1006"
    RATE_LIMIT_ERROR = "COMMON_1007"
    TIMEOUT_ERROR = "COMMON_1008"
    DATABASE_ERROR = "COMMON_1009"

    # 데이터베이스 관련 (2000-2999)
    DATABASE_CONNECTION_ERROR = "DB_2000"
    DATABASE_QUERY_ERROR = "DB_2001"
    DATABASE_TRANSACTION_ERROR = "DB_2002"
    DATABASE_CONSTRAINT_ERROR = "DB_2003"
    DATABASE_DEADLOCK_ERROR = "DB_2004"

    # 메시징 관련 (3000-3999)
    MESSAGE_PUBLISH_ERROR = "MSG_3000"
    MESSAGE_CONSUME_ERROR = "MSG_3001"
    MESSAGE_SERIALIZE_ERROR = "MSG_3002"
    MESSAGE_DESERIALIZE_ERROR = "MSG_3003"

    # 캐시 관련 (4000-4999)
    CACHE_CONNECTION_ERROR = "CACHE_4000"
    CACHE_OPERATION_ERROR = "CACHE_4001"
    CACHE_KEY_NOT_FOUND = "CACHE_4002"

    # 외부 서비스 관련 (5000-5999)
    EXTERNAL_API_ERROR = "EXT_5000"
    EXTERNAL_API_TIMEOUT = "EXT_5001"
    EXTERNAL_API_RATE_LIMIT = "EXT_5002"

# AegisBaseException은 ServiceException의 별칭
AegisBaseException = None  # 나중에 정의됨

class ServiceException(Exception):
    """서비스 예외 베이스 클래스"""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        self.cause = cause
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> Dict[str, Any]:
        """에러 정보를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code
        }

class ValidationError(ServiceException):
    """입력값 검증 에러"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=400
        )

class EntityNotFoundError(ServiceException):
    """엔티티를 찾을 수 없는 에러"""

    def __init__(self, entity_type: str, entity_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"{entity_type} not found: {entity_id}"
        super().__init__(
            error_code=ErrorCode.NOT_FOUND_ERROR,
            message=message,
            details=details or {"entity_type": entity_type, "entity_id": entity_id},
            status_code=404
        )

class DuplicateEntityError(ServiceException):
    """중복 엔티티 에러"""

    def __init__(self, entity_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"{entity_type} already exists"
        super().__init__(
            error_code=ErrorCode.DUPLICATE_ERROR,
            message=message,
            details=details or {"entity_type": entity_type},
            status_code=409
        )

class AuthenticationError(ServiceException):
    """인증 에러"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            message=message,
            details=details,
            status_code=401
        )

class AuthorizationError(ServiceException):
    """인가 에러"""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            message=message,
            details=details,
            status_code=403
        )

class ExternalServiceError(ServiceException):
    """외부 서비스 에러"""

    def __init__(
        self,
        service_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=f"External service error ({service_name}): {message}",
            details=details or {"service_name": service_name},
            status_code=502,
            cause=cause
        )

class DatabaseError(ServiceException):
    """데이터베이스 에러"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            message=f"Database error: {message}",
            details=details,
            status_code=500,
            cause=cause
        )

class MessagePublishError(ServiceException):
    """메시지 발행 에러"""

    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        if topic:
            full_message = f"Message publish error ({topic}): {message}"
            topic_details = details or {"topic": topic}
        else:
            full_message = f"Message publish error: {message}"
            topic_details = details or {}

        super().__init__(
            error_code=ErrorCode.MESSAGE_PUBLISH_ERROR,
            message=full_message,
            details=topic_details,
            status_code=500,
            cause=cause
        )

class CacheError(ServiceException):
    """캐시 에러"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            error_code=ErrorCode.CACHE_OPERATION_ERROR,
            message=f"Cache error: {message}",
            details=details,
            status_code=500,
            cause=cause
        )


class InsufficientPermissionsError(AuthorizationError):
    """권한 부족 에러 (AuthorizationError의 별칭)"""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        details = kwargs.copy()
        super().__init__(message=message, details=details)


class TokenExpiredError(AuthenticationError):
    """토큰 만료 에러"""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message)


class InvalidTokenError(AuthenticationError):
    """유효하지 않은 토큰 에러"""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message)

# AegisBaseException을 ServiceException의 별칭으로 설정
AegisBaseException = ServiceException
