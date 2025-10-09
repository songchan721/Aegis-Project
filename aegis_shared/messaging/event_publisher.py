"""
이벤트 발행자

Kafka를 통한 이벤트 발행 기능을 제공합니다.
"""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from aegis_shared.logging import get_logger, request_id_var, service_name_var

logger = get_logger(__name__)


class EventPublisher:
    """이벤트 발행자"""

    def __init__(self, bootstrap_servers: str, **kwargs):
        """
        이벤트 발행자 초기화

        Args:
            bootstrap_servers: Kafka 부트스트랩 서버
            **kwargs: 추가 Kafka 설정
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None  # 실제 구현에서는 KafkaProducer 사용
        logger.info("Event publisher initialized", servers=bootstrap_servers)

    async def publish(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None,
    ) -> None:
        """
        이벤트 발행

        Args:
            topic: Kafka 토픽
            event_type: 이벤트 타입
            data: 이벤트 데이터
            key: 파티션 키 (선택사항)
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
            "metadata": {
                "service": service_name_var.get(),
                "request_id": request_id_var.get(),
            },
        }

        try:
            # 실제 구현에서는 Kafka Producer를 사용
            logger.info(
                "Event published",
                topic=topic,
                event_type=event_type,
                key=key,
                event=event,
            )
        except Exception as e:
            logger.error(
                "Event publish failed", topic=topic, event_type=event_type, error=str(e)
            )
            raise

    def close(self) -> None:
        """프로듀서 종료"""
        if self.producer:
            self.producer.close()
        logger.info("Event publisher closed")
