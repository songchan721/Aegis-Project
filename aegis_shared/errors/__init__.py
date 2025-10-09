"""
이지스(Aegis) 공유 라이브러리 - 에러 처리 모듈

이 모듈은 중앙 에러 코드 레지스트리와 예외 처리 시스템을 제공합니다.
"""

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    CacheError,
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
    ErrorCode,
    ExternalServiceError,
    MessagePublishError,
    ServiceException,
    ValidationError,
)
from .handlers import ErrorHandler, get_error_handler

__all__ = [
    # 에러 코드
    "ErrorCode",
    # 예외 클래스
    "ServiceException",
    "ValidationError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "AuthenticationError",
    "AuthorizationError",
    "ExternalServiceError",
    "DatabaseError",
    "MessagePublishError",
    "CacheError",
    # 핸들러
    "ErrorHandler",
    "get_error_handler",
]
