import asyncio
import json
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime

from .schemas import VersionedEvent, EventSubscription, DeadLetterEvent
from ..logging import get_logger

logger = get_logger(__name__)

class EventSubscriber:
    """이벤트 구독자"""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: List[str],
        auto_offset_reset: str = "latest"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.auto_offset_reset = auto_offset_reset
        self.consumer = None
        self._is_running = False
        self._handlers: Dict[str, Callable] = {}

    async def start(self):
        """이벤트 구독자 시작"""
        if self._is_running:
            return

        try:
            from aiokafka import AIOKafkaConsumer

            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                max_poll_records=100
            )

            await self.consumer.start()
            self._is_running = True

            logger.info(
                "event_subscriber_started",
                group_id=self.group_id,
                topics=self.topics,
                bootstrap_servers=self.bootstrap_servers
            )

        except Exception as e:
            logger.error("event_subscriber_start_failed", error=str(e))
            raise

    async def stop(self):
        """이벤트 구독자 중지"""
        if self.consumer:
            await self.consumer.stop()
            self._is_running = False
            logger.info("event_subscriber_stopped", group_id=self.group_id)

    def register_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 등록"""
        self._handlers[event_type] = handler
        logger.info("event_handler_registered", event_type=event_type)

    async def consume(self):
        """이벤트 소비"""
        if not self._is_running:
            raise RuntimeError("Event subscriber is not running")

        try:
            async for message in self.consumer:
                try:
                    # 메시지 파싱
                    event_data = message.value
                    event = VersionedEvent(**event_data)

                    # 이벤트 타입 확인
                    event_type = event.event_type

                    # 핸들러 조회 및 실행
                    handler = self._handlers.get(event_type)
                    if handler:
                        await handler(event)
                        logger.debug(
                            "event_processed",
                            event_type=event_type,
                            topic=message.topic,
                            partition=message.partition,
                            offset=message.offset
                        )
                    else:
                        logger.warning(
                            "no_handler_found",
                            event_type=event_type,
                            topic=message.topic
                        )

                except Exception as e:
                    logger.error(
                        "event_processing_failed",
                        error=str(e),
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset
                    )

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
        subscriptions: Optional[List[EventSubscription]] = None
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
    topics: List[str] = None
) -> EventSubscriber:
    """전역 이벤트 구독자 조회"""
    if topics is None:
        topics = ["default-events"]
    return asyncio.run(_subscriber_manager.create_subscriber(name, bootstrap_servers, group_id, topics))
