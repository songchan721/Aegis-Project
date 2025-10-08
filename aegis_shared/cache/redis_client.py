"""
Redis 캐시 클라이언트

Redis 기반 캐싱 기능을 제공합니다.
"""

import json
import functools
from typing import Any, Optional, Callable
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class CacheClient:
    """Redis 캐시 클라이언트"""
    
    def __init__(self, redis_client):
        """
        캐시 클라이언트 초기화
        
        Args:
            redis_client: Redis 클라이언트 인스턴스
        """
        self.redis_client = redis_client
    
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
                return json.loads(value.decode('utf-8'))
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
                return await self.redis_client.setex(key, ttl, serialized_value)
            else:
                return await self.redis_client.set(key, serialized_value)
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
    
    def cached(self, ttl: int = 300):
        """
        캐싱 데코레이터
        
        Args:
            ttl: TTL (초 단위, 기본값: 300초)
            
        Returns:
            데코레이터 함수
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # 캐시 키 생성
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # 캐시에서 조회
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_result
                
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 결과 캐싱
                await self.set(cache_key, result, ttl)
                logger.debug(f"Cache set: {cache_key}")
                
                return result
            
            return wrapper
        return decorator