"""
Test configuration and fixtures for aegis_shared package.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator, Generator
import tempfile
import os
from pathlib import Path

# Test database URL for SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.expire = AsyncMock(return_value=True)
    mock.flushall = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    mock = Mock()
    mock.send = AsyncMock()
    mock.flush = AsyncMock()
    mock.close = AsyncMock()
    return mock

@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer."""
    mock = Mock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.close = AsyncMock()
    mock.__aiter__ = AsyncMock(return_value=iter([]))
    return mock

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_schema_registry_path(temp_dir):
    """Create a temporary schema registry path."""
    schema_path = temp_dir / "schemas"
    schema_path.mkdir(exist_ok=True)
    return str(schema_path)

@pytest.fixture
def sample_jwt_secret():
    """Sample JWT secret for testing."""
    return "test-secret-key-for-jwt-tokens"

@pytest.fixture
def sample_user_payload():
    """Sample user payload for JWT tokens."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "roles": ["user"]
    }

@pytest.fixture
def mock_elasticsearch():
    """Mock Elasticsearch client."""
    mock = Mock()
    mock.index = AsyncMock()
    mock.search = AsyncMock()
    mock.delete = AsyncMock()
    mock.indices = Mock()
    mock.indices.create = AsyncMock()
    mock.indices.delete = AsyncMock()
    mock.indices.exists = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_prometheus_registry():
    """Mock Prometheus registry."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    return mock

@pytest.fixture
def sample_schema_definition():
    """Sample schema definition for testing."""
    return {
        "name": "test_table",
        "owner": "test-service",
        "version": "1.0.0",
        "description": "Test table schema",
        "columns": [
            {
                "name": "id",
                "type": "UUID",
                "nullable": False,
                "primary_key": True
            },
            {
                "name": "name",
                "type": "VARCHAR(100)",
                "nullable": False
            },
            {
                "name": "created_at",
                "type": "TIMESTAMP",
                "nullable": False
            }
        ],
        "references": [],
        "indexes": []
    }

@pytest.fixture
def mock_database_session():
    """Mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    return mock

@pytest.fixture
def mock_sentry():
    """Mock Sentry client."""
    mock = Mock()
    mock.capture_exception = Mock()
    mock.capture_message = Mock()
    return mock

# Environment variables for testing
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    test_env = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_URL": "redis://localhost:6379/0",
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "JWT_SECRET_KEY": "test-secret-key",
        "SENTRY_DSN": "",
        "PROMETHEUS_PORT": "8000"
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Clean up environment variables
    for key in test_env.keys():
        os.environ.pop(key, None)