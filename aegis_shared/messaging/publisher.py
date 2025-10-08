import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from .schemas import VersionedEvent, EventMessage
from ..logging import get_logger

logger = get_logger(__name__)

class EventPublisher:
    """기본 이벤트 발행자"""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self._is_running = False

    async def start(self):
        """이벤트 발행자 시작"""
        if self._is_running:
            return

        try:
            from aiokafka import AIOKafkaProducer

            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v.dict() if hasattr(v, 'dict') else v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                retry_backoff_ms=1000
            )

            await self.producer.start()
            self._is_running = True

            logger.info("event_publisher_started", bootstrap_servers=self.bootstrap_servers)

        except Exception as e:
            logger.error("event_publisher_start_failed", error=str(e))
            raise

    async def stop(self):
        """이벤트 발행자 중지"""
        if self.producer:
            await self.producer.stop()
            self._is_running = False
            logger.info("event_publisher_stopped")

    async def publish(
        self,
        topic: str,
        event: VersionedEvent,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """이벤트 발행"""
        if not self._is_running:
            raise RuntimeError("Event publisher is not running")

        try:
            # 헤더 설정
            if headers is None:
                headers = {}

            # 메시지 생성
            message = EventMessage(
                topic=topic,
                key=key,
                value=event,
                headers=headers
            )

            # 발행
            await self.producer.send_and_wait(
                topic,
                value=message.value,
                key=message.key,
                headers=[(k, v.encode()) for k, v in message.headers.items()]
            )

            logger.info(
                "event_published",
                topic=topic,
                event_type=event.event_type,
                version=event.version,
                key=key
            )

        except Exception as e:
            logger.error(
                "event_publish_failed",
                topic=topic,
                event_type=event.event_type,
                error=str(e)
            )
            raise

class VersionedEventPublisher(EventPublisher):
    """버전 관리되는 이벤트 발행자"""

    def __init__(self, bootstrap_servers: str, source: str):
        super().__init__(bootstrap_servers)
        self.source = source

    async def publish(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        version: str = "1.0.0",
        key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """버전 관리되는 이벤트 발행"""

        # 이벤트 생성
        event = VersionedEvent(
            event_type=event_type,
            version=version,
            timestamp=datetime.utcnow(),
            source=self.source,
            data=data,
            metadata=metadata or {}
        )

        # 발행
        await super().publish(topic, event, key)

class EventPublisherManager:
    """이벤트 발행자 관리자"""

    def __init__(self):
        self.publishers: Dict[str, EventPublisher] = {}
        self._lock = asyncio.Lock()

    async def get_publisher(
        self,
        name: str,
        bootstrap_servers: str,
        source: str = "unknown"
    ) -> VersionedEventPublisher:
        """이벤트 발행자 조회 (싱글톤 패턴)"""
        async with self._lock:
            if name not in self.publishers:
                publisher = VersionedEventPublisher(bootstrap_servers, source)
                await publisher.start()
                self.publishers[name] = publisher

            return self.publishers[name]

    async def close_all(self):
        """모든 발행자 종료"""
        async with self._lock:
            for publisher in self.publishers.values():
                await publisher.stop()
            self.publishers.clear()

# 전역 인스턴스
_publisher_manager = EventPublisherManager()

def get_event_publisher(
    name: str = "default",
    bootstrap_servers: str = "localhost:9092",
    source: str = "aegis-service"
) -> VersionedEventPublisher:
    """전역 이벤트 발행자 조회"""
    return asyncio.run(_publisher_manager.get_publisher(name, bootstrap_servers, source))
