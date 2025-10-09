import asyncio
import json
from typing import Callable, Dict, List, Optional

from ..logging import get_logger
from .schemas import EventSubscription

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
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.auto_offset_reset = auto_offset_reset
        self._consumer = consumer  # Allow DI
        self._is_running = False
        self._handlers: Dict[str, Callable] = {}

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
        try:
            # 메시지 파싱
            event_data = (
                json.loads(message.value.decode("utf-8"))
                if isinstance(message.value, bytes)
                else message.value
            )
            event_type = event_data.get("event_type")

            # 핸들러 조회 및 실행
            handler = self._handlers.get(event_type)
            if handler:
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
                )
            else:
                logger.warning(
                    "no_handler_found",
                    event_type=event_type,
                    topic=getattr(message, "topic", None),
                )

        except Exception as e:
            logger.error(
                "event_processing_failed",
                error=str(e),
                topic=getattr(message, "topic", None),
                partition=getattr(message, "partition", None),
                offset=getattr(message, "offset", None),
            )
            # Don't raise - handle errors gracefully to continue processing
            # other messages

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
