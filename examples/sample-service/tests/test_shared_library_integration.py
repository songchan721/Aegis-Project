"""
Aegis Shared Library 통합 테스트

이 테스트는 shared library의 모든 주요 기능이 올바르게 통합되어 작동하는지 검증합니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

# Shared Library 컴포넌트 테스트
from aegis_shared.database import DatabaseManager, BaseRepository
from aegis_shared.auth import JWTHandler
from aegis_shared.logging import configure_logging, get_logger, add_context
from aegis_shared.messaging import EventPublisher
from aegis_shared.cache import CacheClient
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.errors.exceptions import (
    EntityNotFoundError, ValidationError, TokenExpiredError
)
from aegis_shared.models import BaseEntity, PaginatedResponse
from aegis_shared.config import Settings

class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_database_manager_session(self):
        """데이터베이스 매니저 세션 테스트"""
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
        
        async with db_manager.session() as session:
            assert session is not None
            # 세션이 올바르게 생성되었는지 확인
            assert hasattr(session, 'execute')
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
        
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_base_repository_crud(self):
        """Base Repository CRUD 테스트"""
        # Mock 모델과 세션
        mock_session = AsyncMock()
        mock_model = Mock()
        mock_model.id = "test-id"
        
        # Repository 인스턴스 생성
        repo = BaseRepository(mock_session, mock_model)
        
        # 메서드 존재 확인
        assert hasattr(repo, 'get_by_id')
        assert hasattr(repo, 'create')
        assert hasattr(repo, 'update')
        assert hasattr(repo, 'delete')
        assert hasattr(repo, 'list')
        assert hasattr(repo, 'count')

class TestAuthenticationIntegration:
    """인증 통합 테스트"""
    
    def test_jwt_handler_create_token(self):
        """JWT 토큰 생성 테스트"""
        jwt_handler = JWTHandler("test-secret")
        
        data = {"user_id": "123", "email": "test@example.com"}
        token = jwt_handler.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_jwt_handler_verify_token(self):
        """JWT 토큰 검증 테스트"""
        jwt_handler = JWTHandler("test-secret")
        
        data = {"user_id": "123", "email": "test@example.com"}
        token = jwt_handler.create_access_token(data)
        
        payload = jwt_handler.verify_token(token)
        
        assert payload["user_id"] == "123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_jwt_handler_expired_token(self):
        """만료된 토큰 테스트"""
        jwt_handler = JWTHandler("test-secret")
        
        data = {"user_id": "123"}
        # 이미 만료된 토큰 생성
        token = jwt_handler.create_access_token(
            data, 
            expires_delta=timedelta(seconds=-1)
        )
        
        with pytest.raises(TokenExpiredError):
            jwt_handler.verify_token(token)

class TestLoggingIntegration:
    """로깅 통합 테스트"""
    
    def test_configure_logging(self):
        """로깅 설정 테스트"""
        configure_logging("test-service", "INFO")
        logger = get_logger(__name__)
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
    
    def test_logging_context(self):
        """로깅 컨텍스트 테스트"""
        configure_logging("test-service", "INFO")
        logger = get_logger(__name__)
        
        # 컨텍스트 추가
        add_context(request_id="req-123", user_id="user-456")
        
        # 로그 기록 (실제 출력은 확인하지 않고 에러가 없는지만 확인)
        logger.info("Test log message", extra_field="test")

class TestMessagingIntegration:
    """메시징 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_event_publisher_publish(self):
        """이벤트 발행 테스트"""
        # Mock Kafka Producer
        mock_producer = Mock()
        mock_producer.send.return_value = None
        mock_producer.flush.return_value = None
        
        with patch('aegis_shared.messaging.event_publisher.KafkaProducer', return_value=mock_producer):
            publisher = EventPublisher("localhost:9092")
            
            await publisher.publish(
                topic="test-topic",
                event_type="test.event",
                data={"key": "value"},
                key="test-key"
            )
            
            # Producer 메서드가 호출되었는지 확인
            mock_producer.send.assert_called_once()
            mock_producer.flush.assert_called_once()

class TestCacheIntegration:
    """캐시 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_cache_client_operations(self):
        """캐시 클라이언트 기본 작업 테스트"""
        # Mock Redis 클라이언트
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b'{"key": "value"}'
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        
        cache_client = CacheClient(mock_redis)
        
        # 캐시 설정
        await cache_client.set("test-key", {"key": "value"}, ttl=300)
        mock_redis.set.assert_called_once()
        
        # 캐시 조회
        value = await cache_client.get("test-key")
        mock_redis.get.assert_called_once()
        
        # 캐시 삭제
        await cache_client.delete("test-key")
        mock_redis.delete.assert_called_once()

class TestMonitoringIntegration:
    """모니터링 통합 테스트"""
    
    def test_metrics_collector_initialization(self):
        """메트릭 수집기 초기화 테스트"""
        metrics = MetricsCollector()
        
        assert metrics is not None
        assert hasattr(metrics, 'track_requests')
        assert hasattr(metrics, 'track_database_queries')
        assert hasattr(metrics, 'increment_counter')
        assert hasattr(metrics, 'observe_histogram')
    
    def test_metrics_decorators(self):
        """메트릭 데코레이터 테스트"""
        metrics = MetricsCollector()
        
        @metrics.track_requests()
        def test_function():
            return "test"
        
        # 데코레이터가 적용된 함수 실행
        result = test_function()
        assert result == "test"

class TestErrorHandlingIntegration:
    """에러 처리 통합 테스트"""
    
    def test_custom_exceptions(self):
        """커스텀 예외 테스트"""
        # EntityNotFoundError
        with pytest.raises(EntityNotFoundError) as exc_info:
            raise EntityNotFoundError("User", "123")
        
        assert "User" in str(exc_info.value)
        assert "123" in str(exc_info.value)
        
        # ValidationError
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid input")
        
        assert "Invalid input" in str(exc_info.value)

class TestModelsIntegration:
    """모델 통합 테스트"""
    
    def test_base_entity(self):
        """BaseEntity 테스트"""
        class TestEntity(BaseEntity):
            name: str
            value: int
        
        entity = TestEntity(name="test", value=42)
        
        assert entity.name == "test"
        assert entity.value == 42
        assert entity.id is not None
        assert entity.created_at is not None
        assert entity.updated_at is not None
    
    def test_paginated_response(self):
        """PaginatedResponse 테스트"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        response = PaginatedResponse.create(
            items=items,
            total=10,
            page=1,
            page_size=3
        )
        
        assert response.items == items
        assert response.total == 10
        assert response.page == 1
        assert response.page_size == 3
        assert response.total_pages == 4  # ceil(10/3)

class TestConfigIntegration:
    """설정 통합 테스트"""
    
    def test_settings_loading(self):
        """설정 로드 테스트"""
        class TestSettings(Settings):
            app_name: str = "test-app"
            debug: bool = False
        
        settings = TestSettings()
        
        assert settings.app_name == "test-app"
        assert settings.debug is False

class TestFullIntegration:
    """전체 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """완전한 워크플로우 테스트"""
        # 1. 설정 로드
        class TestSettings(Settings):
            app_name: str = "integration-test"
            jwt_secret: str = "test-secret"
        
        settings = TestSettings()
        
        # 2. 로깅 설정
        configure_logging(settings.app_name, "INFO")
        logger = get_logger(__name__)
        
        # 3. JWT 핸들러
        jwt_handler = JWTHandler(settings.jwt_secret)
        
        # 4. 토큰 생성 및 검증
        token = jwt_handler.create_access_token({"user_id": "123"})
        payload = jwt_handler.verify_token(token)
        
        assert payload["user_id"] == "123"
        
        # 5. 로깅 컨텍스트 설정
        add_context(user_id=payload["user_id"])
        
        # 6. 로그 기록
        logger.info("Integration test completed successfully")
        
        # 7. 메트릭 수집
        metrics = MetricsCollector()
        metrics.increment_counter("integration_test_completed")
        
        # 모든 단계가 에러 없이 완료되면 성공