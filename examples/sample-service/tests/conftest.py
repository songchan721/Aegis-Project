"""
테스트 설정 및 픽스처
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, Mock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app, get_db_session, get_cache, get_event_publisher
from models import Base
from config import SampleServiceSettings

# 테스트 설정
test_settings = SampleServiceSettings(
    database_url="sqlite+aiosqlite:///:memory:",
    redis_url="redis://localhost:6379/1",  # 테스트용 DB
    kafka_bootstrap_servers="localhost:9092",
    jwt_secret="test-secret-key"
)

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 픽스처"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """테스트 데이터베이스 픽스처"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield session_factory
    
    await engine.dispose()

@pytest.fixture
def mock_cache():
    """Mock 캐시 클라이언트"""
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    return cache

@pytest.fixture
def mock_event_publisher():
    """Mock 이벤트 발행자"""
    publisher = AsyncMock()
    publisher.publish.return_value = None
    return publisher

@pytest.fixture
def client(test_db, mock_cache, mock_event_publisher):
    """테스트 클라이언트"""
    
    async def override_get_db():
        async with test_db() as session:
            yield session
    
    def override_get_cache():
        return mock_cache
    
    def override_get_event_publisher():
        return mock_event_publisher
    
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_cache] = override_get_cache
    app.dependency_overrides[get_event_publisher] = override_get_event_publisher
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    """인증 헤더"""
    # 실제로는 JWT 토큰을 생성해야 하지만, 테스트에서는 Mock 사용
    return {"Authorization": "Bearer test-token"}

@pytest.fixture
def sample_user_data():
    """샘플 사용자 데이터"""
    return {
        "email": "test@example.com",
        "name": "Test User"
    }