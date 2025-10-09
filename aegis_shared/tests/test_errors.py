"""
Tests for errors module.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, field_validator

from aegis_shared.errors.exceptions import (
    AegisBaseException,
    ServiceException,
    ValidationError as AegisValidationError,
    EntityNotFoundError,
    DuplicateEntityError,
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
    DatabaseError,
    MessagePublishError,
    CacheError,
    InsufficientPermissionsError,
    TokenExpiredError,
    InvalidTokenError,
    ErrorCode,
)
from aegis_shared.errors.handlers import ErrorHandler


# ============================================================================
# Test 1: Exception Classes
# ============================================================================

class TestExceptionClasses:
    """예외 클래스 테스트"""

    def test_aegis_base_exception_is_service_exception(self):
        """AegisBaseException은 ServiceException의 별칭"""
        assert AegisBaseException is ServiceException

    def test_service_exception_basic(self):
        """ServiceException 기본 속성 테스트"""
        exc = ServiceException(
            error_code="TEST_001",
            message="Test error",
            details={"key": "value"},
            status_code=400
        )
        assert exc.error_code == "TEST_001"
        assert exc.message == "Test error"
        assert exc.details == {"key": "value"}
        assert exc.status_code == 400
        assert isinstance(exc.timestamp, datetime)

    def test_service_exception_to_dict(self):
        """ServiceException to_dict 메서드 테스트"""
        exc = ServiceException(
            error_code="TEST_002",
            message="Test error 2",
            details={"field": "value"},
            status_code=500
        )
        result = exc.to_dict()

        assert result["error_code"] == "TEST_002"
        assert result["message"] == "Test error 2"
        assert result["details"] == {"field": "value"}
        assert result["status_code"] == 500
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_validation_error(self):
        """ValidationError 테스트"""
        exc = AegisValidationError("Invalid input", {"field": "email"})
        assert exc.error_code == ErrorCode.VALIDATION_ERROR
        assert exc.status_code == 400
        assert exc.details == {"field": "email"}

    def test_entity_not_found_error(self):
        """EntityNotFoundError 테스트"""
        exc = EntityNotFoundError("User", "user123")
        assert exc.error_code == ErrorCode.NOT_FOUND_ERROR
        assert exc.status_code == 404
        assert "User not found: user123" in exc.message
        assert exc.details["entity_type"] == "User"
        assert exc.details["entity_id"] == "user123"

    def test_duplicate_entity_error(self):
        """DuplicateEntityError 테스트"""
        exc = DuplicateEntityError("User", {"email": "test@example.com"})
        assert exc.error_code == ErrorCode.DUPLICATE_ERROR
        assert exc.status_code == 409
        assert "User already exists" in exc.message
        assert exc.details == {"email": "test@example.com"}

    def test_authentication_error(self):
        """AuthenticationError 테스트"""
        exc = AuthenticationError("Invalid credentials")
        assert exc.error_code == ErrorCode.AUTHENTICATION_ERROR
        assert exc.status_code == 401
        assert exc.message == "Invalid credentials"

    def test_authorization_error(self):
        """AuthorizationError 테스트"""
        exc = AuthorizationError("Access denied")
        assert exc.error_code == ErrorCode.AUTHORIZATION_ERROR
        assert exc.status_code == 403
        assert exc.message == "Access denied"

    def test_external_service_error(self):
        """ExternalServiceError 테스트"""
        exc = ExternalServiceError("OpenAI", "API timeout")
        assert exc.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert exc.status_code == 502
        assert "OpenAI" in exc.message
        assert "API timeout" in exc.message

    def test_database_error(self):
        """DatabaseError 테스트"""
        exc = DatabaseError("Connection failed")
        assert exc.error_code == ErrorCode.DATABASE_ERROR
        assert exc.status_code == 500
        assert "Connection failed" in exc.message

    def test_message_publish_error(self):
        """MessagePublishError 테스트"""
        exc = MessagePublishError( topic="user.created", message = "Kafka unavailable")
        assert exc.error_code == ErrorCode.MESSAGE_PUBLISH_ERROR
        assert exc.status_code == 500
        assert "user.created" in exc.message
        assert exc.details["topic"] == "user.created"

    def test_cache_error(self):
        """CacheError 테스트"""
        exc = CacheError("Redis connection lost")
        assert exc.error_code == ErrorCode.CACHE_OPERATION_ERROR
        assert exc.status_code == 500
        assert "Redis connection lost" in exc.message

    def test_insufficient_permissions_error(self):
        """InsufficientPermissionsError 테스트"""
        exc = InsufficientPermissionsError("Cannot delete resource", resource="user")
        assert exc.error_code == ErrorCode.AUTHORIZATION_ERROR
        assert exc.status_code == 403
        assert exc.details == {"resource": "user"}

    def test_token_expired_error(self):
        """TokenExpiredError 테스트"""
        exc = TokenExpiredError()
        assert exc.error_code == ErrorCode.AUTHENTICATION_ERROR
        assert exc.status_code == 401
        assert "expired" in exc.message.lower()

    def test_invalid_token_error(self):
        """InvalidTokenError 테스트"""
        exc = InvalidTokenError()
        assert exc.error_code == ErrorCode.AUTHENTICATION_ERROR
        assert exc.status_code == 401
        assert "invalid" in exc.message.lower()


# ============================================================================
# Test 2: Error Handler
# ============================================================================

class TestErrorHandler:
    """에러 핸들러 테스트"""

    @pytest.fixture
    def handler(self):
        return ErrorHandler()

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        return request

    @pytest.mark.asyncio
    async def test_handle_service_exception(self, handler, mock_request):
        """ServiceException 핸들링 테스트"""
        exc = ServiceException(
            error_code="TEST_001",
            message="Test error",
            details={"field": "value"},
            status_code=400
        )

        response = await handler.handle_error(mock_request, exc)

        assert response.status_code == 400
        content = response.body.decode()
        assert "TEST_001" in content
        assert "Test error" in content

    @pytest.mark.asyncio
    async def test_handle_http_exception(self, handler, mock_request):
        """HTTPException 핸들링 테스트"""
        exc = HTTPException(status_code=404, detail="Not found")

        response = await handler.handle_error(mock_request, exc)

        assert response.status_code == 404
        content = response.body.decode()
        assert "HTTP_404" in content
        assert "Not found" in content
        assert "timestamp" in content

    @pytest.mark.asyncio
    async def test_handle_validation_error(self, handler, mock_request):
        """RequestValidationError 핸들링 테스트"""
        # ValidationError를 생성하기 위한 Pydantic 모델
        class TestModel(BaseModel):
            email: str
            age: int

            @field_validator('email')
            @classmethod
            def validate_email(cls, v):
                if '@' not in v:
                    raise ValueError('Invalid email')
                return v

        # ValidationError 발생시키기
        try:
            TestModel(email="invalid", age="not_an_int")
        except ValidationError as ve:
            # RequestValidationError로 래핑
            exc = RequestValidationError([
                {"type": "value_error", "loc": ("body", "email"), "msg": "Invalid email"}
            ])

            response = await handler.handle_error(mock_request, exc)

            assert response.status_code == 422
            content = response.body.decode()
            assert ErrorCode.VALIDATION_ERROR in content
            assert "Validation failed" in content

    @pytest.mark.asyncio
    async def test_handle_generic_exception(self, handler, mock_request):
        """일반 예외 핸들링 테스트"""
        exc = RuntimeError("Unexpected error")

        response = await handler.handle_error(mock_request, exc)

        assert response.status_code == 500
        content = response.body.decode()
        assert ErrorCode.UNKNOWN_ERROR in content
        assert "Internal server error" in content

    @pytest.mark.asyncio
    async def test_register_custom_handler(self, handler, mock_request):
        """커스텀 핸들러 등록 테스트"""
        class CustomException(Exception):
            pass

        async def custom_handler(request, exc):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=418, content={"error": "custom"})

        handler.register_handler(CustomException, custom_handler)

        exc = CustomException("test")
        response = await handler.handle_error(mock_request, exc)

        assert response.status_code == 418


# ============================================================================
# Test 3: Error Code Registry
# ============================================================================

class TestErrorCode:
    """에러 코드 레지스트리 테스트"""

    def test_error_codes_defined(self):
        """주요 에러 코드가 정의되어 있는지 확인"""
        assert hasattr(ErrorCode, 'UNKNOWN_ERROR')
        assert hasattr(ErrorCode, 'VALIDATION_ERROR')
        assert hasattr(ErrorCode, 'AUTHENTICATION_ERROR')
        assert hasattr(ErrorCode, 'AUTHORIZATION_ERROR')
        assert hasattr(ErrorCode, 'NOT_FOUND_ERROR')
        assert hasattr(ErrorCode, 'DUPLICATE_ERROR')
        assert hasattr(ErrorCode, 'DATABASE_ERROR')

    def test_error_code_format(self):
        """에러 코드 형식 검증"""
        assert ErrorCode.VALIDATION_ERROR == "COMMON_1001"
        assert ErrorCode.DATABASE_CONNECTION_ERROR == "DB_2000"
        assert ErrorCode.MESSAGE_PUBLISH_ERROR == "MSG_3000"
        assert ErrorCode.CACHE_CONNECTION_ERROR == "CACHE_4000"
        assert ErrorCode.EXTERNAL_API_ERROR == "EXT_5000"


# ============================================================================
# Test 4: Integration Test
# ============================================================================

async def test_error_response_format():
    """에러 응답 형식 통합 테스트"""
    exc = ServiceException(
        error_code="TEST_001",
        message="Test error",
        details={"key": "value"},
        status_code=400
    )

    response_dict = exc.to_dict()

    # Requirements.md에 명시된 표준 응답 형식 검증
    assert "error_code" in response_dict
    assert "message" in response_dict
    assert "details" in response_dict
    assert "timestamp" in response_dict
    assert "status_code" in response_dict

    # 타입 검증
    assert isinstance(response_dict["error_code"], str)
    assert isinstance(response_dict["message"], str)
    assert isinstance(response_dict["details"], dict)
    assert isinstance(response_dict["timestamp"], str)
    assert isinstance(response_dict["status_code"], int)
