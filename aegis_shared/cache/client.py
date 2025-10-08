import redis.asyncio as redis
from typing import Optional

class RedisClient:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        await self.client.set(key, value, ex=ttl)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def delete_pattern(self, pattern: str):
        async for key in self.client.scan_iter(match=pattern):
            await self.client.delete(key)

    async def close(self):
        await self.client.close()
