import traceback
from datetime import UTC, datetime
from typing import Callable, Dict

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..logging import get_logger
from .exceptions import ErrorCode, ServiceException

logger = get_logger(__name__)


class ErrorHandler:
    """중앙 에러 핸들러"""

    def __init__(self):
        self.error_handlers: Dict[type, Callable] = {
            ServiceException: self._handle_service_exception,
            HTTPException: self._handle_http_exception,
            RequestValidationError: self._handle_validation_error,
            Exception: self._handle_generic_exception,
        }

    def register_handler(self, exception_type: type, handler: Callable):
        """에러 핸들러 등록"""
        self.error_handlers[exception_type] = handler

    async def handle_error(self, request: Request, exc: Exception) -> JSONResponse:
        """에러 처리"""
        handler = self.error_handlers.get(type(exc))

        if handler:
            return await handler(request, exc)
        else:
            # 등록되지 않은 예외 타입
            return await self._handle_generic_exception(request, exc)

    async def _handle_service_exception(
        self, request: Request, exc: ServiceException
    ) -> JSONResponse:
        """서비스 예외 처리"""
        logger.error(
            "service_exception_occurred",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            status_code=exc.status_code,
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )

        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    async def _handle_http_exception(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        """HTTP 예외 처리"""
        logger.warning(
            "http_exception_occurred",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.url.path,
            },
        )

    async def _handle_validation_error(
        self, request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """검증 에러 처리"""
        logger.warning(
            "validation_error_occurred",
            errors=exc.errors(),
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=422,
            content={
                "error_code": ErrorCode.VALIDATION_ERROR,
                "message": "Validation failed",
                "details": {"errors": exc.errors(), "body": exc.body},
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.url.path,
            },
        )

    async def _handle_generic_exception(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """일반 예외 처리"""
        logger.error(
            "unexpected_error_occurred",
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            traceback=traceback.format_exc(),
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error_code": ErrorCode.UNKNOWN_ERROR,
                "message": "Internal server error",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.url.path,
            },
        )


# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """전역 에러 핸들러 조회"""
    return error_handler
