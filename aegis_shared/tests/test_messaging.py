"""
Tests for messaging module.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

# MessagingError는 MessagePublishError의 별칭으로 사용
from aegis_shared.errors.exceptions import MessagePublishError as MessagingError
from aegis_shared.messaging.producer import KafkaProducer
from aegis_shared.messaging.publisher import EventPublisher
from aegis_shared.messaging.schemas import EventMetadata, EventSchema
from aegis_shared.messaging.subscriber import EventSubscriber


class CustomEventSchema(BaseModel):
    """Custom event schema for testing."""

    event_type: str
    user_id: str
    data: dict


class TestKafkaProducer:
    """Test Kafka producer functionality."""

    @pytest.fixture
    def mock_aiokafka_producer(self):
        """Mock aiokafka producer."""
        mock = AsyncMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.send_and_wait = AsyncMock()
        mock.send = AsyncMock()
        return mock

    @pytest.fixture
    def kafka_producer(self, mock_aiokafka_producer):
        """Create Kafka producer with mocked aiokafka."""
        with patch(
            "aegis_shared.messaging.producer.AIOKafkaProducer",
            return_value=mock_aiokafka_producer,
        ):
            producer = KafkaProducer(bootstrap_servers="localhost:9092")
            producer._producer = mock_aiokafka_producer
            return producer

    @pytest.mark.asyncio
    async def test_producer_start(self, kafka_producer, mock_aiokafka_producer):
        """Test producer start."""
        await kafka_producer.start()
        mock_aiokafka_producer.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_producer_stop(self, kafka_producer, mock_aiokafka_producer):
        """Test producer stop."""
        await kafka_producer.stop()
        mock_aiokafka_producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, kafka_producer, mock_aiokafka_producer):
        """Test sending message."""
        message = {"key": "value", "timestamp": datetime.now(UTC).isoformat()}

        await kafka_producer.send("test-topic", message)

        mock_aiokafka_producer.send_and_wait.assert_called_once()
        call_args = mock_aiokafka_producer.send_and_wait.call_args

        assert call_args[0][0] == "test-topic"  # topic

        # Verify message was serialized (second positional argument)
        sent_value = call_args[0][1]
        assert isinstance(sent_value, bytes)

        # Verify message content
        deserialized = json.loads(sent_value.decode("utf-8"))
        assert deserialized["key"] == "value"

    @pytest.mark.asyncio
    async def test_send_message_with_key(self, kafka_producer, mock_aiokafka_producer):
        """Test sending message with key."""
        message = {"data": "test"}
        key = "test-key"

        await kafka_producer.send("test-topic", message, key=key)

        call_args = mock_aiokafka_producer.send_and_wait.call_args
        assert call_args.kwargs["key"] == key.encode("utf-8")

    @pytest.mark.asyncio
    async def test_send_message_error_handling(
        self, kafka_producer, mock_aiokafka_producer
    ):
        """Test error handling during message send."""
        mock_aiokafka_producer.send_and_wait.side_effect = Exception("Kafka error")

        with pytest.raises(MessagingError):
            await kafka_producer.send("test-topic", {"data": "test"})

    @pytest.mark.asyncio
    async def test_batch_send(self, kafka_producer, mock_aiokafka_producer):
        """Test batch message sending."""
        messages = [
            {"id": 1, "data": "message1"},
            {"id": 2, "data": "message2"},
            {"id": 3, "data": "message3"},
        ]

        await kafka_producer.send_batch("test-topic", messages)

        # Should call send_and_wait for each message
        assert mock_aiokafka_producer.send_and_wait.call_count == 3

    @pytest.mark.asyncio
    async def test_producer_context_manager(self, mock_aiokafka_producer):
        """Test producer as context manager."""
        with patch(
            "aegis_shared.messaging.producer.AIOKafkaProducer",
            return_value=mock_aiokafka_producer,
        ):
            async with KafkaProducer(bootstrap_servers="localhost:9092") as producer:
                await producer.send("test-topic", {"data": "test"})

            # Should start and stop automatically
            mock_aiokafka_producer.start.assert_called_once()
            mock_aiokafka_producer.stop.assert_called_once()


class TestEventPublisher:
    """Test event publisher functionality."""

    @pytest.fixture
    def mock_kafka_producer(self):
        """Mock Kafka producer."""
        mock = AsyncMock()
        mock.send = AsyncMock()
        return mock

    @pytest.fixture
    def event_publisher(self, mock_kafka_producer):
        """Create event publisher with mocked Kafka producer."""
        publisher = EventPublisher(kafka_producer=mock_kafka_producer)
        return publisher

    @pytest.mark.asyncio
    async def test_publish_event(self, event_publisher, mock_kafka_producer):
        """Test event publishing."""
        event_data = {
            "user_id": "user-123",
            "action": "policy_created",
            "policy_id": "policy-456",
        }

        await event_publisher.publish(
            topic="policy-events", event_type="policy.created", data=event_data
        )

        mock_kafka_producer.send.assert_called_once()
        call_args = mock_kafka_producer.send.call_args

        assert call_args[0][0] == "policy-events"  # topic

        # Verify event structure
        event = call_args[0][1]
        assert event["event_type"] == "policy.created"
        assert event["data"] == event_data
        assert "timestamp" in event
        assert "metadata" in event

    @pytest.mark.asyncio
    async def test_publish_event_with_metadata(
        self, event_publisher, mock_kafka_producer
    ):
        """Test event publishing with metadata."""
        with patch("aegis_shared.logging.context.get_context") as mock_get_context:
            mock_get_context.return_value = {
                "request_id": "req-123",
                "user_id": "user-456",
                "service_name": "policy-service",
            }

            await event_publisher.publish(
                topic="policy-events",
                event_type="policy.updated",
                data={"policy_id": "policy-789"},
            )

            call_args = mock_kafka_producer.send.call_args
            event = call_args[0][1]

            # Verify metadata was added
            metadata = event["metadata"]
            assert metadata["request_id"] == "req-123"
            assert metadata["user_id"] == "user-456"
            assert metadata["service_name"] == "policy-service"

    @pytest.mark.asyncio
    async def test_publish_event_with_key(self, event_publisher, mock_kafka_producer):
        """Test event publishing with message key."""
        await event_publisher.publish(
            topic="user-events",
            event_type="user.created",
            data={"user_id": "user-123"},
            key="user-123",
        )

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["key"] == "user-123"

    @pytest.mark.asyncio
    async def test_publish_batch_events(self, event_publisher, mock_kafka_producer):
        """Test batch event publishing."""
        events = [
            {"event_type": "user.created", "data": {"user_id": "user-1"}},
            {"event_type": "user.created", "data": {"user_id": "user-2"}},
            {"event_type": "user.created", "data": {"user_id": "user-3"}},
        ]

        await event_publisher.publish_batch("user-events", events)

        # Should call send for each event
        assert mock_kafka_producer.send.call_count == 3


class TestEventSubscriber:
    """Test event subscriber functionality."""

    @pytest.fixture
    def mock_aiokafka_consumer(self):
        """Mock aiokafka consumer."""
        mock = AsyncMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.subscribe = AsyncMock()
        mock.unsubscribe = AsyncMock()
        mock.__aiter__ = AsyncMock()
        return mock

    @pytest.fixture
    def event_subscriber(self, mock_aiokafka_consumer):
        """Create event subscriber with mocked aiokafka."""
        subscriber = EventSubscriber(
            bootstrap_servers="localhost:9092",
            group_id="test-group",
            topics=["test-topic"],
            consumer=mock_aiokafka_consumer,  # Inject mock consumer
        )
        return subscriber

    @pytest.mark.asyncio
    async def test_subscriber_start(self, event_subscriber, mock_aiokafka_consumer):
        """Test subscriber start."""
        await event_subscriber.start()

        mock_aiokafka_consumer.start.assert_called_once()
        mock_aiokafka_consumer.subscribe.assert_called_once_with(["test-topic"])

    @pytest.mark.asyncio
    async def test_subscriber_stop(self, event_subscriber, mock_aiokafka_consumer):
        """Test subscriber stop."""
        await event_subscriber.stop()

        mock_aiokafka_consumer.unsubscribe.assert_called_once()
        mock_aiokafka_consumer.stop.assert_called_once()

    def test_register_handler(self, event_subscriber):
        """Test event handler registration."""

        def test_handler(event):
            return f"Handled: {event['event_type']}"

        event_subscriber.register_handler("user.created", test_handler)

        assert "user.created" in event_subscriber.handlers
        assert event_subscriber.handlers["user.created"] == test_handler

    def test_register_handler_decorator(self, event_subscriber):
        """Test event handler registration using decorator."""

        @event_subscriber.handler("policy.created")
        def policy_created_handler(event):
            return f"Policy created: {event['data']['policy_id']}"

        assert "policy.created" in event_subscriber.handlers
        assert event_subscriber.handlers["policy.created"] == policy_created_handler

    @pytest.mark.asyncio
    async def test_process_message(self, event_subscriber):
        """Test message processing."""
        # Register handler
        handled_events = []

        def test_handler(event):
            handled_events.append(event)

        event_subscriber.register_handler("test.event", test_handler)

        # Create mock message
        mock_message = Mock()
        event_data = {
            "event_type": "test.event",
            "data": {"test": "data"},
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": {"service_name": "test-service"},
        }
        mock_message.value = json.dumps(event_data).encode("utf-8")

        # Process message
        await event_subscriber._process_message(mock_message)

        # Verify handler was called
        assert len(handled_events) == 1
        assert handled_events[0]["event_type"] == "test.event"
        assert handled_events[0]["data"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_process_message_no_handler(self, event_subscriber):
        """Test processing message with no registered handler."""
        mock_message = Mock()
        event_data = {"event_type": "unknown.event", "data": {"test": "data"}}
        mock_message.value = json.dumps(event_data).encode("utf-8")

        # Should not raise exception
        await event_subscriber._process_message(mock_message)

    @pytest.mark.asyncio
    async def test_process_message_handler_error(self, event_subscriber):
        """Test processing message when handler raises error."""

        def failing_handler(event):
            raise ValueError("Handler error")

        event_subscriber.register_handler("error.event", failing_handler)

        mock_message = Mock()
        event_data = {"event_type": "error.event", "data": {"test": "data"}}
        mock_message.value = json.dumps(event_data).encode("utf-8")

        # Should handle error gracefully
        await event_subscriber._process_message(mock_message)

    @pytest.mark.asyncio
    async def test_process_invalid_message(self, event_subscriber):
        """Test processing invalid JSON message."""
        mock_message = Mock()
        mock_message.value = b"invalid json"

        # Should handle invalid JSON gracefully
        await event_subscriber._process_message(mock_message)


class TestEventSchema:
    """Test event schema functionality."""

    def test_event_metadata_creation(self):
        """Test event metadata creation."""
        metadata = EventMetadata(
            service_name="test-service", request_id="req-123", user_id="user-456"
        )

        assert metadata.service_name == "test-service"
        assert metadata.request_id == "req-123"
        assert metadata.user_id == "user-456"
        assert metadata.timestamp is not None

    def test_event_schema_validation(self):
        """Test event schema validation."""
        event_data = {
            "event_type": "user.created",
            "version": "1.0.0",
            "source": "user-service",
            "data": {"user_id": "user-123", "email": "test@example.com"},
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": {
                "service_name": "user-service",
                "request_id": "req-123",
                "version": "1.0.0",
                "source": "user-service",
            },
        }

        event = EventSchema(**event_data)

        assert event.event_type == "user.created"
        assert event.data["user_id"] == "user-123"
        assert event.metadata["service_name"] == "user-service"

    def test_event_schema_validation_error(self):
        """Test event schema validation with invalid data."""
        invalid_data = {
            "event_type": "user.created",
            # Missing required fields
        }

        with pytest.raises(ValueError):
            EventSchema(**invalid_data)

    def test_custom_event_schema(self):
        """Test custom event schema."""
        event_data = {
            "event_type": "user.created",
            "user_id": "user-123",
            "data": {"email": "test@example.com"},
        }

        event = CustomEventSchema(**event_data)

        assert event.event_type == "user.created"
        assert event.user_id == "user-123"
        assert event.data["email"] == "test@example.com"


class TestMessagingIntegration:
    """Test messaging integration scenarios."""

    @pytest.mark.asyncio
    async def test_publisher_subscriber_integration(self):
        """Test integration between publisher and subscriber."""
        # Mock Kafka components
        mock_producer = AsyncMock()
        mock_consumer = AsyncMock()

        # Create publisher and subscriber
        publisher = EventPublisher(kafka_producer=mock_producer)

        subscriber = EventSubscriber(
            bootstrap_servers="localhost:9092",
            group_id="test-group",
            topics=["integration-topic"],
            consumer=mock_consumer,
        )

        # Register handler
        received_events = []

        @subscriber.handler("integration.test")
        def integration_handler(event):
            received_events.append(event)

        # Publish event
        await publisher.publish(
            topic="integration-topic",
            event_type="integration.test",
            data={"test_id": "test-123"},
        )

        # Verify publisher called Kafka producer
        mock_producer.send.assert_called_once()

        # Simulate message consumption
        call_args = mock_producer.send.call_args
        published_event = call_args[0][1]

        mock_message = Mock()
        mock_message.value = json.dumps(published_event).encode("utf-8")

        await subscriber._process_message(mock_message)

        # Verify event was processed
        assert len(received_events) == 1
        assert received_events[0]["event_type"] == "integration.test"
        assert received_events[0]["data"]["test_id"] == "test-123"
