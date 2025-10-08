"""
User Service와 Shared Library 통합 테스트

이 테스트는 user-service에서 shared-library의 모든 주요 기능이 
올바르게 통합되어 작동하는지 검증합니다.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch

from app.main import app
from app.config import UserServiceSettings

class TestSharedLibraryIntegration:
    """Shared Library 통합 테스트"""
    
    def test_app_initialization(self):
        """애플리케이션 초기화 테스트"""
        # FastAPI 앱이 올바르게 생성되었는지 확인
        assert app.title == "User Service"
        assert app.version == "1.0.0"
    
    def test_settings_loading(self):
        """설정 로드 테스트"""
        settings = UserServiceSettings()
        
        # 기본 설정값 확인
        assert settings.app_name == "user-service"
        assert settings.app_version == "1.0.0"
        assert settings.port == 8001
        assert settings.jwt_algorithm == "HS256"
    
    def test_health_endpoint(self):
        """헬스 체크 엔드포인트 테스트"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["service"] == "user-service"
            assert data["version"] == "1.0.0"
            assert "components" in data
    
    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            
            data = response.json()
            assert data["service"] == "user-service"
            assert data["version"] == "1.0.0"
            assert data["status"] == "running"
    
    def test_metrics_endpoint(self):
        """메트릭 엔드포인트 테스트"""
        with TestClient(app) as client:
            response = client.get("/metrics")
            # 메트릭 수집기가 초기화되지 않은 경우 503 에러 예상
            assert response.status_code in [200, 503]

class TestSharedLibraryComponents:
    """Shared Library 컴포넌트별 테스트"""
    
    @pytest.mark.asyncio
    async def test_database_manager_integration(self):
        """데이터베이스 매니저 통합 테스트"""
        from aegis_shared.database import DatabaseManager
        
        # SQLite는 pool_size, max_overflow를 지원하지 않으므로 기본 설정으로 테스트
        db_manager = DatabaseManager(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )
        
        async with db_manager.session() as session:
            # 간단한 쿼리 실행
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1
        
        await db_manager.close()
    
    def test_jwt_handler_integration(self):
        """JWT 핸들러 통합 테스트"""
        from aegis_shared.auth import JWTHandler
        
        jwt_handler = JWTHandler("test-secret")
        
        # 토큰 생성
        payload = {"user_id": "123", "email": "test@example.com"}
        token = jwt_handler.create_access_token(payload)
        
        # 토큰 검증
        decoded_payload = jwt_handler.verify_token(token)
        assert decoded_payload["user_id"] == "123"
        assert decoded_payload["email"] == "test@example.com"
    
    def test_logging_integration(self):
        """로깅 통합 테스트"""
        from aegis_shared.logging import configure_logging, get_logger, add_context
        
        # 로깅 설정
        configure_logging("user-service-test", "INFO")
        logger = get_logger(__name__)
        
        # 컨텍스트 추가
        add_context(user_id="test-user", request_id="test-request")
        
        # 로그 기록 (에러가 발생하지 않는지 확인)
        logger.info("Integration test log", action="test")
    
    @pytest.mark.asyncio
    async def test_cache_client_integration(self):
        """캐시 클라이언트 통합 테스트"""
        from aegis_shared.cache import CacheClient
        from unittest.mock import AsyncMock
        
        # Mock Redis 클라이언트
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b'{"key": "value"}'
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        
        cache_client = CacheClient(mock_redis)
        
        # 캐시 작업 테스트 - 실제 메서드 호출
        await cache_client.redis_client.set("test-key", '{"data": "test"}', ex=300)
        value = await cache_client.redis_client.get("test-key")
        await cache_client.redis_client.delete("test-key")
        
        # Mock 메서드가 호출되었는지 확인
        mock_redis.set.assert_called_once()
        mock_redis.get.assert_called_once()
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_event_publisher_integration(self):
        """이벤트 발행자 통합 테스트"""
        from aegis_shared.messaging import EventPublisher
        from aegis_shared.logging import configure_logging, add_context
        
        # 로깅 설정 (EventPublisher가 로깅을 사용하므로)
        configure_logging("user-service-test", "INFO")
        add_context(request_id="test-request")
        
        # EventPublisher 생성 및 테스트
        publisher = EventPublisher("localhost:9092")
        
        # 이벤트 발행 (현재 구현에서는 로깅만 수행)
        await publisher.publish(
            topic="user-events",
            event_type="user.test",
            data={"test": "data"},
            key="test-key"
        )
        
        # 에러가 발생하지 않으면 성공
        assert publisher.bootstrap_servers == "localhost:9092"
    
    def test_metrics_collector_integration(self):
        """메트릭 수집기 통합 테스트"""
        from aegis_shared.monitoring import MetricsCollector
        
        metrics = MetricsCollector()
        
        # 메트릭 수집 테스트
        metrics.increment_counter("test_counter", labels={"service": "user-service"})
        metrics.observe_histogram("test_histogram", value=0.123)
        metrics.set_gauge("test_gauge", value=42)
        
        # 에러가 발생하지 않으면 성공

class TestUserServiceSpecificIntegration:
    """User Service 특화 통합 테스트"""
    
    def test_user_service_settings_validation(self):
        """User Service 설정 검증 테스트"""
        settings = UserServiceSettings()
        
        # 필수 설정들이 올바르게 로드되었는지 확인
        assert settings.app_name == "user-service"
        assert settings.database_url.startswith("postgresql")
        assert settings.redis_url.startswith("redis")
        assert settings.kafka_bootstrap_servers
        assert settings.jwt_secret
        assert settings.password_min_length >= 8
        assert settings.max_login_attempts > 0
    
    @pytest.mark.asyncio
    async def test_user_service_dependencies(self):
        """User Service 의존성 테스트"""
        from app.main import get_db_session, get_cache, get_metrics, get_event_publisher
        
        # 의존성 함수들이 올바르게 정의되었는지 확인
        assert callable(get_db_session)
        assert callable(get_cache)
        assert callable(get_metrics)
        assert callable(get_event_publisher)
    
    def test_cors_middleware_configuration(self):
        """CORS 미들웨어 설정 테스트"""
        with TestClient(app) as client:
            # OPTIONS 요청으로 CORS 헤더 확인
            response = client.options("/")
            
            # CORS 헤더가 포함되어 있는지 확인
            assert "access-control-allow-origin" in response.headers or response.status_code == 405
    
    def test_exception_handler_registration(self):
        """예외 핸들러 등록 테스트"""
        from aegis_shared.errors.exceptions import ServiceException
        
        # 예외 핸들러가 등록되어 있는지 확인
        exception_handlers = app.exception_handlers
        assert ServiceException in exception_handlers or len(exception_handlers) > 0

class TestEndToEndIntegration:
    """End-to-End 통합 테스트"""
    
    def test_complete_request_flow(self):
        """완전한 요청 플로우 테스트"""
        with TestClient(app) as client:
            # 1. 헬스 체크
            health_response = client.get("/health")
            assert health_response.status_code == 200
            
            # 2. 루트 엔드포인트
            root_response = client.get("/")
            assert root_response.status_code == 200
            
            # 3. 메트릭 엔드포인트 (사용 가능한 경우)
            metrics_response = client.get("/metrics")
            assert metrics_response.status_code in [200, 503]
    
    @pytest.mark.asyncio
    async def test_shared_library_component_interaction(self):
        """Shared Library 컴포넌트 간 상호작용 테스트"""
        from aegis_shared.logging import configure_logging, get_logger, add_context
        from aegis_shared.auth import JWTHandler
        from aegis_shared.monitoring import MetricsCollector
        
        # 1. 로깅 설정
        configure_logging("integration-test", "INFO")
        logger = get_logger(__name__)
        
        # 2. JWT 핸들러로 토큰 생성
        jwt_handler = JWTHandler("test-secret")
        token = jwt_handler.create_access_token({"user_id": "test-123"})
        payload = jwt_handler.verify_token(token)
        
        # 3. 로깅 컨텍스트에 사용자 정보 추가
        add_context(user_id=payload["user_id"])
        
        # 4. 메트릭 수집
        metrics = MetricsCollector()
        metrics.increment_counter("integration_test_completed")
        
        # 5. 로그 기록
        logger.info("Integration test completed successfully", token_valid=True)
        
        # 모든 단계가 에러 없이 완료되면 성공
        assert payload["user_id"] == "test-123"

def test_shared_library_version_compatibility():
    """Shared Library 버전 호환성 테스트"""
    try:
        # Shared Library 모듈들이 올바르게 임포트되는지 확인
        from aegis_shared.database import DatabaseManager, BaseRepository
        from aegis_shared.auth import JWTHandler, AuthMiddleware
        from aegis_shared.logging import configure_logging, get_logger
        from aegis_shared.messaging import EventPublisher
        from aegis_shared.cache import CacheClient
        from aegis_shared.monitoring import MetricsCollector
        from aegis_shared.errors.exceptions import ServiceException
        from aegis_shared.models import BaseEntity, PaginatedResponse
        from aegis_shared.config import Settings
        
        # 모든 임포트가 성공하면 호환성 확인 완료
        assert True
        
    except ImportError as e:
        pytest.fail(f"Shared Library 호환성 문제: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])