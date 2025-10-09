"""
Redis 캐시 클라이언트

Redis 기반 캐싱 기능을 제공합니다.
"""

import json
import functools
from typing import Any, Optional, Callable, List
from aegis_shared.logging import get_logger
from prometheus_client import Counter

logger = get_logger(__name__)

CACHE_HITS = Counter("cache_hits_total", "Total cache hits", ["function"])
CACHE_MISSES = Counter("cache_misses_total", "Total cache misses", ["function"])

class CacheClient:
    """Redis 캐시 클라이언트"""
    
    def __init__(self, redis_client):
        """
        캐시 클라이언트 초기화

        Args:
            redis_client: Redis 클라이언트 인스턴스
        """
        self.redis_client = redis_client
        self._hit_count = 0
        self._miss_count = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        try:
            value = await self.redis_client.get(key)
            if value:
                # decode_responses=True면 이미 문자열, 아니면 bytes
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}", key=key)
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초 단위)

        Returns:
            성공 여부
        """
        try:
            serialized_value = json.dumps(value, ensure_ascii=False)
            if ttl:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}", key=key)
            return False
    
    async def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제
        
        Args:
            key: 캐시 키
            
        Returns:
            성공 여부
        """
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}", key=key)
            return False
    
    def cached(self, ttl: int = 300, key_prefix: str = ""):
        """
        캐싱 데코레이터

        Args:
            ttl: TTL (초 단위, 기본값: 300초)
            key_prefix: 캐시 키 접두사

        Returns:
            데코레이터 함수
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # 캐시 키 생성
                func_name = func.__name__
                args_hash = hash(str(args) + str(sorted(kwargs.items())))
                cache_key = f"{key_prefix}{func_name}:{args_hash}"

                # 캐시에서 조회
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    self._hit_count += 1
                    CACHE_HITS.labels(function=func_name).inc()
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_result

                # 캐시 미스
                self._miss_count += 1
                CACHE_MISSES.labels(function=func_name).inc()

                # 함수 실행
                result = await func(*args, **kwargs)

                # 결과 캐싱
                await self.set(cache_key, result, ttl)
                logger.debug(f"Cache miss, set: {cache_key}")

                return result

            return wrapper
        return decorator

    async def delete_pattern(self, pattern: str) -> int:
        """
        패턴에 매칭되는 모든 키 삭제

        Args:
            pattern: Redis 패턴 (예: "user:*")

        Returns:
            삭제된 키의 개수
        """
        try:
            deleted_count = 0
            async for key in self.redis_client.scan_iter(match=pattern):
                await self.redis_client.delete(key)
                deleted_count += 1
            logger.info(f"Deleted {deleted_count} keys matching pattern: {pattern}")
            return deleted_count
        except Exception as e:
            logger.error(f"Cache delete_pattern error: {e}", pattern=pattern)
            return 0

    async def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}", key=key)
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        패턴에 매칭되는 모든 키 조회

        Args:
            pattern: Redis 패턴 (기본값: "*")

        Returns:
            키 리스트
        """
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            return keys
        except Exception as e:
            logger.error(f"Cache keys error: {e}", pattern=pattern)
            return []

    def get_hit_rate(self) -> float:
        """
        캐시 히트율 조회

        Returns:
            히트율 (0.0 ~ 1.0)
        """
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return self._hit_count / total

    async def close(self):
        """Redis 연결 종료"""
        try:
            # aclose()가 있으면 사용, 없으면 close() 사용
            if hasattr(self.redis_client, 'aclose'):
                await self.redis_client.aclose()
            else:
                await self.redis_client.close()
        except Exception as e:
            logger.error(f"Cache close error: {e}")