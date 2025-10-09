import asyncio
import json
from datetime import UTC, datetime
from typing import Callable, Dict, List, Optional

from ..logging import get_logger
from .schemas import DeadLetterEvent, EventSubscription, VersionedEvent

logger = get_logger(__name__)


class EventSubscriber:
    """이벤트 구독자"""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: List[str],
        auto_offset_reset: str = "latest",
        consumer=None,  # For dependency injection (testing)
        max_retries: int = 3,
        dlq_topic: str = "dlq",
        publisher=None,  # EventPublisher for DLQ
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.auto_offset_reset = auto_offset_reset
        self._consumer = consumer  # Allow DI
        self._is_running = False
        self._handlers: Dict[str, Callable] = {}
        self.max_retries = max_retries
        self.dlq_topic = dlq_topic
        self._publisher = publisher

    async def start(self):
        """이벤트 구독자 시작"""
        if self._is_running:
            return

        try:
            # Only create consumer if not injected
            if self._consumer is None:
                from aiokafka import AIOKafkaConsumer

                self._consumer = AIOKafkaConsumer(
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    auto_offset_reset=self.auto_offset_reset,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    key_deserializer=lambda m: m.decode("utf-8") if m else None,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000,
                    max_poll_records=100,
                )

            # Subscribe to topics
            self._consumer.subscribe(self.topics)
            await self._consumer.start()
            self._is_running = True

            logger.info(
                "event_subscriber_started",
                group_id=self.group_id,
                topics=self.topics,
                bootstrap_servers=self.bootstrap_servers,
            )

        except Exception as e:
            logger.error("event_subscriber_start_failed", error=str(e))
            raise

    async def stop(self):
        """이벤트 구독자 중지"""
        if self._consumer:
            self._consumer.unsubscribe()
            await self._consumer.stop()
            self._is_running = False
            logger.info("event_subscriber_stopped", group_id=self.group_id)

    @property
    def handlers(self):
        """Get registered handlers"""
        return self._handlers

    def register_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 등록"""
        self._handlers[event_type] = handler
        logger.info("event_handler_registered", event_type=event_type)

    def handler(self, event_type: str):
        """데코레이터 형태로 이벤트 핸들러 등록"""

        def decorator(func: Callable):
            self.register_handler(event_type, func)
            return func

        return decorator

    async def _process_message(self, message):
        """메시지 처리"""
        event_data = None
        first_failure = None
        retry_count = 0

        try:
            # 메시지 파싱
            event_data = (
                json.loads(message.value.decode("utf-8"))
                if isinstance(message.value, bytes)
                else message.value
            )
            event_type = event_data.get("event_type")

            # 핸들러 조회 및 실행 (재시도 로직 포함)
            handler = self._handlers.get(event_type)
            if handler:
                # Retry logic
                for attempt in range(self.max_retries + 1):
                    try:
                        retry_count = attempt
                        # Handler can be sync or async
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event_data)
                        else:
                            handler(event_data)

                        logger.debug(
                            "event_processed",
                            event_type=event_type,
                            topic=getattr(message, "topic", None),
                            partition=getattr(message, "partition", None),
                            offset=getattr(message, "offset", None),
                            retry_count=attempt,
                        )
                        # Success - exit retry loop
                        return

                    except Exception as handler_error:
                        if first_failure is None:
                            first_failure = datetime.now(UTC)

                        if attempt < self.max_retries:
                            # Retry with exponential backoff
                            backoff = 2**attempt
                            logger.warning(
                                "event_processing_retry",
                                error=str(handler_error),
                                event_type=event_type,
                                attempt=attempt + 1,
                                max_retries=self.max_retries,
                                backoff_seconds=backoff,
                            )
                            await asyncio.sleep(backoff)
                        else:
                            # Max retries reached - send to DLQ
                            logger.error(
                                "event_processing_failed_max_retries",
                                error=str(handler_error),
                                event_type=event_type,
                                retry_count=retry_count,
                            )
                            await self._send_to_dlq(
                                event_data=event_data,
                                error_message=str(handler_error),
                                error_type=type(handler_error).__name__,
                                retry_count=retry_count,
                                first_failure=first_failure,
                            )
                            # Don't raise - continue processing other messages
                            return
            else:
                logger.warning(
                    "no_handler_found",
                    event_type=event_type,
                    topic=getattr(message, "topic", None),
                )

        except Exception as e:
            # Parsing or other unexpected errors
            logger.error(
                "event_processing_failed",
                error=str(e),
                topic=getattr(message, "topic", None),
                partition=getattr(message, "partition", None),
                offset=getattr(message, "offset", None),
            )
            # Send to DLQ if we have event data
            if event_data:
                await self._send_to_dlq(
                    event_data=event_data,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    retry_count=0,
                    first_failure=datetime.now(UTC),
                )

    async def _send_to_dlq(
        self,
        event_data: dict,
        error_message: str,
        error_type: str,
        retry_count: int,
        first_failure: datetime,
    ) -> None:
        """Send failed event to Dead Letter Queue."""
        try:
            if not self._publisher:
                logger.warning(
                    "dlq_publisher_not_configured",
                    error_message=error_message,
                )
                return

            # Reconstruct VersionedEvent from event_data
            versioned_event = VersionedEvent(
                event_type=event_data.get("event_type", "unknown"),
                version=event_data.get("version", "1.0.0"),
                timestamp=event_data.get("timestamp", datetime.now(UTC).isoformat()),
                source=event_data.get("source", "unknown"),
                data=event_data.get("data", {}),
                metadata=event_data.get("metadata", {}),
            )

            now = datetime.now(UTC)
            dlq_event_dict = {
                "original_event": versioned_event.model_dump(),
                "error_message": error_message,
                "error_type": error_type,
                "retry_count": retry_count,
                "first_failure": first_failure.isoformat(),
                "last_failure": now.isoformat(),
            }

            # Send to DLQ using publisher
            dlq_message = json.dumps(dlq_event_dict).encode("utf-8")

            if hasattr(self._publisher, "producer") and self._publisher.producer:
                producer = self._publisher.producer
                is_mock = hasattr(producer, "_is_mock") and producer._is_mock

                if is_mock:
                    await producer.send(self.dlq_topic, dlq_event_dict)
                else:
                    await producer.send_and_wait(self.dlq_topic, value=dlq_message)

                logger.info(
                    "event_sent_to_dlq",
                    dlq_topic=self.dlq_topic,
                    error_type=error_type,
                    retry_count=retry_count,
                )
        except Exception as dlq_error:
            logger.error(
                "dlq_send_failed",
                error=str(dlq_error),
                original_error=error_message,
            )

    async def consume(self):
        """이벤트 소비"""
        if not self._is_running:
            raise RuntimeError("Event subscriber is not running")

        try:
            async for message in self._consumer:
                await self._process_message(message)

        except Exception as e:
            logger.error("event_consumption_failed", error=str(e))
            raise


class EventSubscriberManager:
    """이벤트 구독자 관리자"""

    def __init__(self):
        self.subscribers: Dict[str, EventSubscriber] = {}
        self._lock = asyncio.Lock()

    async def create_subscriber(
        self,
        name: str,
        bootstrap_servers: str,
        group_id: str,
        topics: List[str],
        subscriptions: Optional[List[EventSubscription]] = None,
    ) -> EventSubscriber:
        """이벤트 구독자 생성"""
        async with self._lock:
            if name in self.subscribers:
                raise ValueError(f"Subscriber '{name}' already exists")

            subscriber = EventSubscriber(bootstrap_servers, group_id, topics)

            # 구독 정보 등록
            if subscriptions:
                for subscription in subscriptions:
                    # 핸들러 등록 로직 (실제 구현 시 동적 로딩 필요)
                    pass

            await subscriber.start()
            self.subscribers[name] = subscriber

            return subscriber

    async def get_subscriber(self, name: str) -> EventSubscriber:
        """이벤트 구독자 조회"""
        if name not in self.subscribers:
            raise ValueError(f"Subscriber '{name}' not found")
        return self.subscribers[name]

    async def close_all(self):
        """모든 구독자 종료"""
        async with self._lock:
            for subscriber in self.subscribers.values():
                await subscriber.stop()
            self.subscribers.clear()


# 전역 인스턴스
_subscriber_manager = EventSubscriberManager()


def get_event_subscriber(
    name: str = "default",
    bootstrap_servers: str = "localhost:9092",
    group_id: str = "aegis-consumer",
    topics: List[str] = None,
) -> EventSubscriber:
    """전역 이벤트 구독자 조회"""
    if topics is None:
        topics = ["default-events"]
    return asyncio.run(
        _subscriber_manager.create_subscriber(name, bootstrap_servers, group_id, topics)
    )
