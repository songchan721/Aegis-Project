import json
from typing import List, Optional

from aiokafka import AIOKafkaProducer

from aegis_shared.errors.exceptions import MessagePublishError


class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self.producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def send(self, topic: str, message: dict, key: Optional[str] = None):
        """Send a single message to Kafka topic."""
        try:
            value = json.dumps(message).encode("utf-8")
            kafka_key = key.encode("utf-8") if key else None
            await self.producer.send_and_wait(topic, value, key=kafka_key)
        except Exception as e:
            raise MessagePublishError(
                f"Failed to send message: {e}", topic=topic
            ) from e

    async def send_batch(self, topic: str, messages: List[dict]):
        """Send multiple messages to Kafka topic."""
        try:
            for message in messages:
                await self.send(topic, message)
        except Exception as e:
            raise MessagePublishError(
                f"Failed to send batch messages: {e}", topic=topic
            ) from e

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
        return False
