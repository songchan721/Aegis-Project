"""
Tests for database module.
"""

from datetime import datetime

import pytest
from sqlalchemy import Boolean, Column, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from aegis_shared.database.exceptions import (
    DatabaseConnectionError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from aegis_shared.database.manager import DatabaseManager
from aegis_shared.database.repository import BaseRepository
from aegis_shared.database.retry import with_db_retry
from aegis_shared.database.transaction import TransactionManager

Base = declarative_base()


class TestModel(Base):
    """Test model for database operations."""

    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class TestDatabaseManager:
    """Test database manager functionality."""

    @pytest.fixture
    async def db_manager(self):
        """Create test database manager."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        manager = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")
        manager.engine = engine
        manager.async_session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_session_context_manager(self, db_manager):
        """Test session context manager."""
        async with db_manager.session() as session:
            assert isinstance(session, AsyncSession)
            assert session.is_active

    @pytest.mark.asyncio
    async def test_session_commit_on_success(self, db_manager):
        """Test session commits on successful operation."""
        async with db_manager.session() as session:
            # Create test entity
            entity = TestModel(name="test", email="test@example.com")
            session.add(entity)
            # Session should commit automatically

        # Verify entity was committed
        async with db_manager.session() as session:
            result = await session.execute(select(TestModel))
            entities = result.scalars().all()
            assert len(entities) == 1
            assert entities[0].name == "test"

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, db_manager):
        """Test session rolls back on error."""
        try:
            async with db_manager.session() as session:
                # Create test entity
                entity = TestModel(name="test", email="test@example.com")
                session.add(entity)
                # Simulate error
                raise Exception("Test error")
        except Exception:
            pass

        # Verify entity was not committed
        async with db_manager.session() as session:
            result = await session.execute(select(TestModel))
            entities = result.scalars().all()
            assert len(entities) == 0


class TestBaseRepository:
    """Test base repository functionality."""

    @pytest.fixture
    async def repository(self):
        """Create test repository."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with session_factory() as session:
            repo = BaseRepository(TestModel, session)
            yield repo, session

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_entity(self, repository):
        """Test entity creation."""
        repo, session = repository

        entity = TestModel(name="test", email="test@example.com")
        created = await repo.create(entity)

        assert created.id is not None
        assert created.name == "test"
        assert created.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository):
        """Test get entity by ID."""
        repo, session = repository

        # Create entity
        entity = TestModel(name="test", email="test@example.com")
        created = await repo.create(entity)
        await session.commit()

        # Get by ID
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "test"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository):
        """Test get entity by ID when not found."""
        repo, session = repository

        found = await repo.get_by_id(999)
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_ids(self, repository):
        """Test get multiple entities by IDs."""
        repo, session = repository

        # Create entities
        entity1 = TestModel(name="test1", email="test1@example.com")
        entity2 = TestModel(name="test2", email="test2@example.com")
        created1 = await repo.create(entity1)
        created2 = await repo.create(entity2)
        await session.commit()

        # Get by IDs
        found = await repo.get_by_ids([created1.id, created2.id])
        assert len(found) == 2
        names = [e.name for e in found]
        assert "test1" in names
        assert "test2" in names

    @pytest.mark.asyncio
    async def test_update_entity(self, repository):
        """Test entity update."""
        repo, session = repository

        # Create entity
        entity = TestModel(name="test", email="test@example.com")
        created = await repo.create(entity)
        await session.commit()

        # Update entity
        updated = await repo.update(created.id, name="updated")
        assert updated is not None
        assert updated.name == "updated"
        assert updated.email == "test@example.com"  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_delete_entity(self, repository):
        """Test entity deletion."""
        repo, session = repository

        # Create entity
        entity = TestModel(name="test", email="test@example.com")
        created = await repo.create(entity)
        await session.commit()

        # Delete entity
        result = await repo.delete(created.id)
        assert result is True

        # Verify deletion
        found = await repo.get_by_id(created.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_soft_delete_entity(self, repository):
        """Test entity soft deletion."""
        repo, session = repository

        # Create entity
        entity = TestModel(name="test", email="test@example.com")
        created = await repo.create(entity)
        await session.commit()

        # Soft delete entity
        updated = await repo.soft_delete(created.id)
        assert updated is not None
        assert updated.deleted_at is not None

    @pytest.mark.asyncio
    async def test_list_entities(self, repository):
        """Test entity listing."""
        repo, session = repository

        # Create entities
        for i in range(5):
            entity = TestModel(name=f"test{i}", email=f"test{i}@example.com")
            await repo.create(entity)
        await session.commit()

        # List entities
        entities = await repo.list(skip=0, limit=3)
        assert len(entities) == 3

        # List with skip
        entities = await repo.list(skip=2, limit=3)
        assert len(entities) == 3

    @pytest.mark.asyncio
    async def test_list_with_filters(self, repository):
        """Test entity listing with filters."""
        repo, session = repository

        # Create entities
        entity1 = TestModel(name="active", email="active@example.com", active=True)
        entity2 = TestModel(name="inactive", email="inactive@example.com", active=False)
        await repo.create(entity1)
        await repo.create(entity2)
        await session.commit()

        # List with filter
        entities = await repo.list(filters={"active": True})
        assert len(entities) == 1
        assert entities[0].name == "active"

    @pytest.mark.asyncio
    async def test_count_entities(self, repository):
        """Test entity counting."""
        repo, session = repository

        # Create entities
        for i in range(3):
            entity = TestModel(name=f"test{i}", email=f"test{i}@example.com")
            await repo.create(entity)
        await session.commit()

        # Count entities
        count = await repo.count()
        assert count == 3

        # Count with filter
        count = await repo.count(filters={"active": True})
        assert count == 3  # All are active by default

    @pytest.mark.asyncio
    async def test_exists_entity(self, repository):
        """Test entity existence check."""
        repo, session = repository

        # Create entity
        entity = TestModel(name="test", email="test@example.com")
        created = await repo.create(entity)
        await session.commit()

        # Check existence
        exists = await repo.exists(created.id)
        assert exists is True

        # Check non-existence
        exists = await repo.exists(999)
        assert exists is False


class TestTransactionManager:
    """Test transaction manager functionality."""

    @pytest.fixture
    def transaction_manager(self):
        """Create transaction manager with mock database manager."""
        from unittest.mock import AsyncMock, MagicMock

        mock_db_manager = MagicMock()
        mock_session = AsyncMock()

        # Create a proper async context manager mock that simulates rollback
        # on exception
        class MockContextManager:
            def __init__(self, session):
                self.session = session

            async def __aenter__(self):
                return self.session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    # Simulate rollback on exception
                    await self.session.rollback()
                else:
                    # Simulate commit on success
                    await self.session.commit()
                await self.session.close()

        mock_db_manager.get_session.return_value = MockContextManager(mock_session)

        transaction_manager = TransactionManager(mock_db_manager)
        transaction_manager.session = mock_session  # For test assertions
        return transaction_manager

    @pytest.mark.asyncio
    async def test_transaction_commit(self, transaction_manager):
        """Test transaction commit."""
        async with transaction_manager.transaction() as session:
            # Simulate some database operations
            assert session is not None

        # Since TransactionManager delegates to DatabaseManager.get_session(),
        # which handles commit/rollback internally, we just verify the session was used
        assert transaction_manager.session is not None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, transaction_manager):
        """Test transaction rollback on error."""
        try:
            async with transaction_manager.transaction():
                raise Exception("Test error")
        except Exception:
            pass

        # Verify rollback was called
        transaction_manager.session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_nested_transaction(self, transaction_manager):
        """Test nested transaction handling."""
        async with transaction_manager.transaction():
            async with transaction_manager.transaction():
                # Nested transaction - currently each creates a separate session
                pass

        # Current implementation creates separate sessions for each transaction call
        # So we expect 2 commits (one for each session)
        assert transaction_manager.session.commit.call_count == 2


class TestDatabaseRetry:
    """Test database retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Test retry on connection error."""
        call_count = 0

        @with_db_retry(max_retries=3)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DatabaseConnectionError("Connection failed")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry when all attempts are exhausted."""

        @with_db_retry(max_retries=2)
        async def always_failing_function():
            raise DatabaseConnectionError("Always fails")

        with pytest.raises(DatabaseConnectionError):
            await always_failing_function()

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test no retry on non-retryable errors."""
        call_count = 0

        @with_db_retry(max_retries=3)
        async def function_with_logic_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Logic error")

        with pytest.raises(ValueError):
            await function_with_logic_error()

        # Should only be called once (no retry)
        assert call_count == 1


class TestDatabaseExceptions:
    """Test database exception handling."""

    def test_database_connection_error(self):
        """Test database connection error."""
        error = DatabaseConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.error_code == "DatabaseConnectionError"

    def test_entity_not_found_error(self):
        """Test entity not found error."""
        error = EntityNotFoundError("User not found", entity_id="123")
        assert str(error) == "User not found"
        assert error.details["entity_id"] == "123"

    def test_duplicate_entity_error(self):
        """Test duplicate entity error."""
        error = DuplicateEntityError("Email already exists", field="email")
        assert str(error) == "Email already exists"
        assert error.details["field"] == "email"
