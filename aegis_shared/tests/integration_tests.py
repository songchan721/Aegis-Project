"""
Integration tests for aegis_shared package.

These tests verify the interaction between different modules
and external dependencies like databases, message queues, and caches.
"""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from aegis_shared.auth.jwt import JWTHandler
from aegis_shared.auth.middleware import AuthMiddleware
from aegis_shared.cache.redis_client import CacheClient
from aegis_shared.config.loader import ConfigLoader

# Test imports
from aegis_shared.database.connection import DatabaseManager
from aegis_shared.database.repository import BaseRepository
from aegis_shared.logging.config import configure_logging, get_logger
from aegis_shared.logging.context import add_context, clear_context
from aegis_shared.messaging.publisher import EventPublisher
from aegis_shared.messaging.subscriber import EventSubscriber
from aegis_shared.migration.coordinator import MigrationCoordinator
from aegis_shared.monitoring.metrics import MetricsCollector
from aegis_shared.schemas.registry import SchemaRegistry


class TestDatabaseIntegration:
    """Test database integration with real database."""

    @pytest.fixture
    async def db_manager(self):
        """Create database manager with SQLite for testing."""
        db_url = "sqlite+aiosqlite:///test_integration.db"
        manager = DatabaseManager(database_url=db_url)

        # Create test tables
        from sqlalchemy import Column, DateTime, Integer, String, create_engine
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()

        class TestUser(Base):
            __tablename__ = "test_users"
            id = Column(Integer, primary_key=True)
            email = Column(String(255), unique=True)
            name = Column(String(100))
            created_at = Column(DateTime, default=datetime.utcnow)

        # Create tables
        engine = create_engine("sqlite:///test_integration.db")
        Base.metadata.create_all(engine)

        yield manager, TestUser

        # Cleanup
        await manager.close()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

    @pytest.mark.asyncio
    async def test_database_repository_integration(self, db_manager):
        """Test database repository with real database operations."""
        manager, TestUser = db_manager

        async with manager.session() as session:
            repo = BaseRepository(TestUser, session)

            # Create user
            user = TestUser(email="test@example.com", name="Test User")
            created_user = await repo.create(user)

            assert created_user.id is not None
            assert created_user.email == "test@example.com"

            # Get user
            found_user = await repo.get_by_id(created_user.id)
            assert found_user is not None
            assert found_user.email == "test@example.com"

            # Update user
            updated_user = await repo.update(created_user.id, name="Updated User")
            assert updated_user.name == "Updated User"

            # List users
            users = await repo.list()
            assert len(users) == 1

            # Count users
            count = await repo.count()
            assert count == 1

            # Delete user
            deleted = await repo.delete(created_user.id)
            assert deleted is True

            # Verify deletion
            found_user = await repo.get_by_id(created_user.id)
            assert found_user is None


class TestAuthenticationIntegration:
    """Test authentication integration."""

    @pytest.fixture
    def auth_components(self):
        """Create authentication components."""
        jwt_handler = JWTHandler(secret_key="test-secret-key-for-integration")
        auth_middleware = AuthMiddleware(jwt_handler=jwt_handler)
        return jwt_handler, auth_middleware

    @pytest.mark.asyncio
    async def test_jwt_middleware_integration(self, auth_components):
        """Test JWT token creation and middleware validation."""
        jwt_handler, auth_middleware = auth_components

        # Create user payload
        user_payload = {
            "user_id": "user-123",
            "email": "test@example.com",
            "roles": ["user", "policy_reader"],
        }

        # Create token
        token = jwt_handler.create_access_token(user_payload)
        assert token is not None

        # Create mock request with token
        from types import SimpleNamespace

        mock_request = Mock()
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = SimpleNamespace()

        # Mock response
        async def mock_call_next(request):
            return Mock(status_code=200)

        # Process through middleware
        await auth_middleware(mock_request, mock_call_next)

        # Verify user info was extracted
        assert hasattr(mock_request.state, "user")
        assert mock_request.state.user_id == "user-123"
        assert mock_request.state.user["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_expired_token_handling(self, auth_components):
        """Test expired token handling in middleware."""
        jwt_handler, auth_middleware = auth_components

        # Create expired token
        user_payload = {"user_id": "user-123"}
        expired_token = jwt_handler.create_access_token(
            user_payload, expires_delta=timedelta(seconds=-1)
        )

        # Create mock request with expired token
        from types import SimpleNamespace

        mock_request = Mock()
        mock_request.headers = {"Authorization": f"Bearer {expired_token}"}
        mock_request.state = SimpleNamespace()

        async def mock_call_next(request):
            return Mock(status_code=200)

        # Process through middleware
        await auth_middleware(mock_request, mock_call_next)

        # Should not set user info for expired token
        assert not hasattr(mock_request.state, "user")


class TestLoggingIntegration:
    """Test logging integration with context and structured output."""

    def setup_method(self):
        """Set up logging for each test."""
        configure_logging(service_name="integration-test", log_level="DEBUG")
        clear_context()

    def teardown_method(self):
        """Clean up after each test."""
        clear_context()

    def test_logging_with_auth_context(self, caplog):
        """Test logging integration with authentication context."""
        import logging

        caplog.set_level(logging.INFO)

        logger = get_logger(__name__)

        # Simulate authentication flow
        add_context(request_id="req-123")
        logger.info("request_started", endpoint="/api/policies")

        # Simulate user authentication
        add_context(user_id="user-456")
        logger.info("user_authenticated", method="jwt")

        # Simulate business logic
        logger.info("policy_retrieved", policy_id="policy-789", count=5)

        # Verify logging calls were made
        assert len(caplog.records) >= 3
        # Verify context was properly set
        assert any("request_started" in record.message for record in caplog.records)
        assert any("user_authenticated" in record.message for record in caplog.records)
        assert any("policy_retrieved" in record.message for record in caplog.records)

    def test_error_logging_with_full_context(self):
        """Test error logging with full context information."""
        logger = get_logger(__name__)

        # Set full context
        add_context(
            request_id="req-123", user_id="user-456", service_name="integration-test"
        )

        try:
            # Simulate error
            raise ValueError("Integration test error")
        except ValueError as e:
            logger.error(
                "integration_test_error",
                error_type=type(e).__name__,
                error_message=str(e),
                component="test_integration",
            )

        # Test passes if no exception is raised during logging


class TestMessagingIntegration:
    """Test messaging integration between publisher and subscriber."""

    @pytest.fixture
    def messaging_components(self):
        """Create messaging components with mocks."""
        mock_kafka_producer = AsyncMock()
        mock_kafka_consumer = AsyncMock()

        publisher = EventPublisher(kafka_producer=mock_kafka_producer)

        with patch("aiokafka.AIOKafkaConsumer", return_value=mock_kafka_consumer):
            subscriber = EventSubscriber(
                bootstrap_servers="localhost:9092",
                group_id="integration-test",
                topics=["integration-events"],
            )

        return publisher, subscriber, mock_kafka_producer, mock_kafka_consumer

    @pytest.mark.asyncio
    async def test_event_publishing_and_consumption(self, messaging_components):
        """Test event publishing and consumption flow."""
        publisher, subscriber, mock_producer, mock_consumer = messaging_components

        # Set up event handler
        received_events = []

        @subscriber.handler("user.created")
        def user_created_handler(event):
            received_events.append(event)

        # Publish event with context
        add_context(request_id="req-123", user_id="user-456")

        await publisher.publish(
            topic="integration-events",
            event_type="user.created",
            data={"user_id": "new-user-789", "email": "newuser@example.com"},
            key="new-user-789",
        )

        # Verify event was sent to Kafka
        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args

        assert call_args[0][0] == "integration-events"  # topic
        assert call_args.kwargs["key"] == "new-user-789"

        # Get the published event
        published_event = call_args[0][1]

        # Simulate message consumption
        mock_message = Mock()
        mock_message.value = json.dumps(published_event).encode("utf-8")

        await subscriber._process_message(mock_message)

        # Verify event was processed
        assert len(received_events) == 1
        event = received_events[0]
        assert event["event_type"] == "user.created"
        assert event["data"]["user_id"] == "new-user-789"
        assert event["metadata"]["request_id"] == "req-123"


class TestCacheIntegration:
    """Test cache integration with Redis-like operations."""

    @pytest.fixture
    def cache_client(self, mock_redis):
        """Create cache client with mock Redis."""
        return CacheClient(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_cache_operations_integration(self, cache_client, mock_redis):
        """Test cache operations integration."""
        # Test set and get with TTL (uses setex)
        await cache_client.set("test_key", {"data": "test_value"}, ttl=300)
        mock_redis.setex.assert_called()

        # Mock get response
        mock_redis.get.return_value = json.dumps({"data": "test_value"}).encode()

        value = await cache_client.get("test_key")
        assert value["data"] == "test_value"

        # Test delete
        await cache_client.delete("test_key")
        mock_redis.delete.assert_called_with("test_key")

    @pytest.mark.asyncio
    async def test_cache_decorator_integration(self, cache_client, mock_redis):
        """Test cache decorator integration."""
        call_count = 0

        @cache_client.cached(ttl=300)
        async def expensive_operation(param1, param2):
            nonlocal call_count
            call_count += 1
            return f"result_{param1}_{param2}"

        # First call - should execute function
        result1 = await expensive_operation("a", "b")
        assert result1 == "result_a_b"
        assert call_count == 1

        # Verify cache was set (uses setex with ttl)
        mock_redis.setex.assert_called()

        # Mock cache hit for second call
        # Cache key format: {func_name}:{hash(args+kwargs)}
        mock_redis.get.return_value = json.dumps("result_a_b").encode()

        # Second call - should use cache
        result2 = await expensive_operation("a", "b")
        assert result2 == "result_a_b"
        # In real scenario with working Redis, function would not be called again


class TestMonitoringIntegration:
    """Test monitoring integration across components."""

    @pytest.fixture
    def monitoring_setup(self):
        """Set up monitoring components."""
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry()
        metrics_collector = MetricsCollector(registry=registry)

        return metrics_collector, registry

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring(self, monitoring_setup):
        """Test end-to-end monitoring integration."""
        metrics_collector, registry = monitoring_setup

        # Create monitored function
        @metrics_collector.track_requests()
        @metrics_collector.track_database_queries()
        async def monitored_business_function(user_id):
            # Simulate database query
            await asyncio.sleep(0.01)

            # Simulate business logic
            return f"processed_user_{user_id}"

        # Execute function multiple times
        for i in range(5):
            result = await monitored_business_function(f"user-{i}")
            assert result == f"processed_user_user-{i}"

        # Get metrics output
        metrics_output = metrics_collector.get_metrics_output()
        assert isinstance(metrics_output, str)
        assert len(metrics_output) > 0


class TestConfigurationIntegration:
    """Test configuration integration."""

    @pytest.fixture
    def config_setup(self, temp_dir):
        """Set up configuration files."""
        # Create .env file
        env_file = temp_dir / ".env"
        env_content = """
DATABASE_URL=sqlite:///test.db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=test-secret-key
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content)

        # Create config file
        config_file = temp_dir / "config.yaml"
        config_content = """
service:
  name: integration-test
  version: 1.0.0

database:
  pool_size: 10
  max_overflow: 20

cache:
  default_ttl: 300
"""
        config_file.write_text(config_content)

        return str(env_file), str(config_file)

    def test_configuration_loading_integration(self, config_setup):
        """Test configuration loading from multiple sources."""
        env_file, config_file = config_setup

        # Set environment variables
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        os.environ["JWT_SECRET"] = "test-secret-key"
        os.environ["PORT"] = "8080"
        os.environ["APP_NAME"] = "integration-test"

        try:
            config_loader = ConfigLoader()
            settings = config_loader.load()

            # Test configuration access
            assert settings.database_url == "sqlite:///test.db"
            assert settings.jwt_secret == "test-secret-key"
            assert settings.port == 8080
            assert settings.app_name == "integration-test"

            # Test ConfigLoader convenience methods
            assert config_loader.get("database_url") == "sqlite:///test.db"
            assert config_loader.get("port") == 8080

        finally:
            # Cleanup
            for key in ["DATABASE_URL", "JWT_SECRET", "PORT", "APP_NAME"]:
                os.environ.pop(key, None)


class TestSchemaRegistryIntegration:
    """Test schema registry integration."""

    @pytest.fixture
    def schema_registry_setup(self, temp_dir):
        """Set up schema registry."""
        schema_path = temp_dir / "schemas"
        schema_path.mkdir()

        # Create sample schema files
        users_schema = {
            "name": "users",
            "owner": "user-service",
            "version": "1.0.0",
            "description": "User table schema",
            "columns": [
                {
                    "name": "id",
                    "type": "UUID",
                    "description": "Primary key",
                    "required": True,
                },
                {
                    "name": "email",
                    "type": "VARCHAR(255)",
                    "description": "User email",
                    "required": True,
                },
                {
                    "name": "name",
                    "type": "VARCHAR(100)",
                    "description": "User name",
                    "required": True,
                },
            ],
            "references": [],
        }

        policies_schema = {
            "name": "policies",
            "owner": "policy-service",
            "version": "1.0.0",
            "description": "Policy table schema",
            "columns": [
                {
                    "name": "id",
                    "type": "UUID",
                    "description": "Primary key",
                    "required": True,
                },
                {
                    "name": "title",
                    "type": "VARCHAR(200)",
                    "description": "Policy title",
                    "required": True,
                },
                {
                    "name": "created_by",
                    "type": "UUID",
                    "description": "User who created policy",
                    "required": True,
                },
            ],
            "references": [{"service": "user-service", "schema": "users"}],
        }

        import yaml

        with open(schema_path / "users.yaml", "w") as f:
            yaml.dump(users_schema, f)

        with open(schema_path / "policies.yaml", "w") as f:
            yaml.dump(policies_schema, f)

        return str(schema_path)

    def test_schema_registry_integration(self, schema_registry_setup):
        """Test schema registry with migration coordination."""
        schema_path = schema_registry_setup

        # Create schema registry
        registry = SchemaRegistry(schema_dir=schema_path)

        # Verify schemas were loaded
        users_schema = registry.get_schema("users")
        policies_schema = registry.get_schema("policies")

        assert users_schema is not None
        assert policies_schema is not None
        assert users_schema.owner == "user-service"
        assert policies_schema.owner == "policy-service"

        # Test dependency analysis
        dependent_services = registry.get_dependent_services("users")
        assert "policy-service" in dependent_services

        # Test migration order
        migration_order = registry.generate_migration_order()
        users_index = migration_order.index("users")
        policies_index = migration_order.index("policies")
        assert users_index < policies_index  # users should come before policies

        # Test validation
        errors = registry.validate_references()
        assert len(errors) == 0  # Should have no validation errors

    def test_migration_coordinator_integration(self, schema_registry_setup):
        """Test migration coordinator integration."""
        schema_path = schema_registry_setup

        registry = SchemaRegistry(schema_dir=schema_path)
        coordinator = MigrationCoordinator(schema_registry=registry)

        # Plan migration
        schema_changes = {
            "users": "ALTER TABLE users ADD COLUMN phone VARCHAR(20);",
            "policies": "ALTER TABLE policies ADD COLUMN description TEXT;",
        }

        steps = coordinator.plan_migration(schema_changes)

        # Verify migration steps
        assert len(steps) == 2

        # Find users and policies steps
        users_step = next(s for s in steps if s.schema == "users")
        policies_step = next(s for s in steps if s.schema == "policies")

        assert users_step.service == "user-service"
        assert policies_step.service == "policy-service"
        assert "ALTER TABLE users" in users_step.sql
        assert "ALTER TABLE policies" in policies_step.sql


class TestFullStackIntegration:
    """Test full stack integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_request_flow(self):
        """Test complete request flow with all components."""
        # Set up components
        configure_logging(service_name="integration-test")
        clear_context()

        jwt_handler = JWTHandler(secret_key="integration-test-secret")

        # Mock external dependencies
        mock_redis = AsyncMock()
        mock_kafka_producer = AsyncMock()

        cache_client = CacheClient(redis_client=mock_redis)
        publisher = EventPublisher(kafka_producer=mock_kafka_producer)

        logger = get_logger(__name__)

        # Simulate request flow
        request_id = "req-integration-123"
        user_payload = {"user_id": "user-456", "email": "test@example.com"}

        # 1. Start request
        add_context(request_id=request_id)
        logger.info("request_started", endpoint="/api/integration-test")

        # 2. Authenticate user
        token = jwt_handler.create_access_token(user_payload)
        verified_payload = jwt_handler.verify_token(token)

        add_context(user_id=verified_payload["user_id"])
        logger.info("user_authenticated", user_id=verified_payload["user_id"])

        # 3. Check cache
        cache_key = f"user_data_{verified_payload['user_id']}"
        mock_redis.get.return_value = None  # Cache miss

        cached_data = await cache_client.get(cache_key)
        assert cached_data is None

        # 4. Simulate business logic
        business_data = {
            "user_id": verified_payload["user_id"],
            "processed_at": datetime.now(UTC).isoformat(),
            "result": "integration_test_success",
        }

        logger.info("business_logic_executed", result=business_data["result"])

        # 5. Cache result
        await cache_client.set(cache_key, business_data, ttl=300)
        mock_redis.setex.assert_called_once()

        # 6. Publish event
        await publisher.publish(
            topic="integration-events",
            event_type="integration.test.completed",
            data=business_data,
            key=verified_payload["user_id"],
        )

        mock_kafka_producer.send.assert_called_once()

        # 7. Complete request
        logger.info("request_completed", status="success", duration_ms=150)

        # Verify the flow completed successfully
        assert business_data["result"] == "integration_test_success"
        assert verified_payload["user_id"] == "user-456"
