from functools import wraps
import json
from .client import RedisClient

from prometheus_client import Counter

CACHE_HITS = Counter("cache_hits_total", "Total cache hits", ["function"])
CACHE_MISSES = Counter("cache_misses_total", "Total cache misses", ["function"])

def cache_result(redis_client: RedisClient, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"
            
            # Try to get the result from cache
            cached_result = await redis_client.get(key)
            if cached_result:
                CACHE_HITS.labels(func.__name__).inc()
                return json.loads(cached_result)
            
            # If not in cache, call the function and cache the result
            CACHE_MISSES.labels(func.__name__).inc()
            result = await func(*args, **kwargs)
            await redis_client.set(key, json.dumps(result), ttl=ttl)
            return result
        return wrapper
    return decorator
