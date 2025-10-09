import fakeredis.aioredis
import pytest

from aegis_shared.cache.redis_client import CacheClient


@pytest.fixture
async def redis_client():
    """FakeRedis 클라이언트 fixture"""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake_redis
    await fake_redis.flushall()
    if hasattr(fake_redis, "aclose"):
        await fake_redis.aclose()
    else:
        await fake_redis.close()


@pytest.fixture
async def cache_client(redis_client):
    """CacheClient fixture"""
    client = CacheClient(redis_client)
    yield client
    await client.close()


# ============================================================================
# Test 1: Basic Cache Operations
# ============================================================================


class TestBasicCacheOperations:
    """기본 캐시 작업 테스트"""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_client):
        """캐시 set/get 기본 동작 테스트"""
        key = "test_key"
        value = {"name": "John", "age": 30}

        # Set
        result = await cache_client.set(key, value)
        assert result is True

        # Get
        cached_value = await cache_client.get(key)
        assert cached_value == value

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_client):
        """존재하지 않는 키 조회 테스트"""
        value = await cache_client.get("nonexistent_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_client, redis_client):
        """TTL 설정 테스트"""
        key = "ttl_key"
        value = "test_value"

        await cache_client.set(key, value, ttl=10)

        # TTL 확인 (fakeredis는 TTL 명령어 지원)
        ttl = await redis_client.ttl(key)
        assert ttl > 0
        assert ttl <= 10

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, cache_client):
        """존재하는 키 삭제 테스트"""
        key = "delete_key"
        value = "test_value"

        await cache_client.set(key, value)
        result = await cache_client.delete(key)

        assert result is True

        # 삭제 후 조회
        cached_value = await cache_client.get(key)
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache_client):
        """존재하지 않는 키 삭제 테스트"""
        result = await cache_client.delete("nonexistent_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, cache_client):
        """키 존재 여부 확인 테스트"""
        key = "exists_key"

        # 키가 없을 때
        exists = await cache_client.exists(key)
        assert exists is False

        # 키 추가
        await cache_client.set(key, "value")

        # 키가 있을 때
        exists = await cache_client.exists(key)
        assert exists is True

    @pytest.mark.asyncio
    async def test_complex_data_types(self, cache_client):
        """복잡한 데이터 타입 저장/조회 테스트"""
        test_cases = [
            ("string_key", "simple string"),
            ("int_key", 12345),
            ("float_key", 123.45),
            ("list_key", [1, 2, 3, "four"]),
            ("dict_key", {"nested": {"data": [1, 2, 3]}}),
            ("bool_key", True),
            ("null_key", None),
        ]

        for key, value in test_cases:
            await cache_client.set(key, value)
            cached_value = await cache_client.get(key)
            assert cached_value == value, f"Failed for {key}"


# ============================================================================
# Test 2: Pattern-based Operations
# ============================================================================


class TestPatternOperations:
    """패턴 기반 작업 테스트"""

    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache_client):
        """패턴 기반 삭제 테스트"""
        # 여러 키 생성
        await cache_client.set("user:1", {"id": 1})
        await cache_client.set("user:2", {"id": 2})
        await cache_client.set("user:3", {"id": 3})
        await cache_client.set("product:1", {"id": 1})

        # 패턴 기반 삭제
        deleted_count = await cache_client.delete_pattern("user:*")
        assert deleted_count == 3

        # 확인
        assert await cache_client.get("user:1") is None
        assert await cache_client.get("user:2") is None
        assert await cache_client.get("user:3") is None
        assert await cache_client.get("product:1") is not None

    @pytest.mark.asyncio
    async def test_keys_pattern(self, cache_client):
        """패턴 기반 키 조회 테스트"""
        # 여러 키 생성
        await cache_client.set("app:user:1", {"id": 1})
        await cache_client.set("app:user:2", {"id": 2})
        await cache_client.set("app:product:1", {"id": 1})

        # 패턴 매칭
        user_keys = await cache_client.keys("app:user:*")
        assert len(user_keys) == 2
        assert "app:user:1" in user_keys
        assert "app:user:2" in user_keys

        # 모든 키
        all_keys = await cache_client.keys("app:*")
        assert len(all_keys) == 3


# ============================================================================
# Test 3: Caching Decorator
# ============================================================================


class TestCachingDecorator:
    """캐싱 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_cached_decorator_basic(self, cache_client):
        """캐싱 데코레이터 기본 동작 테스트"""
        call_count = 0

        @cache_client.cached(ttl=60)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 첫 호출 - 함수 실행
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 두 번째 호출 - 캐시에서 조회
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 함수가 다시 호출되지 않음

        # 다른 인자로 호출 - 함수 실행
        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_with_kwargs(self, cache_client):
        """kwargs를 사용한 캐싱 데코레이터 테스트"""
        call_count = 0

        @cache_client.cached(ttl=60)
        async def get_user(user_id: int, include_deleted: bool = False) -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "deleted": include_deleted}

        # 첫 호출
        result1 = await get_user(1, include_deleted=True)
        assert call_count == 1

        # 같은 인자로 호출 - 캐시 히트
        result2 = await get_user(1, include_deleted=True)
        assert call_count == 1
        assert result1 == result2

        # 다른 kwargs - 캐시 미스
        await get_user(1, include_deleted=False)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_with_key_prefix(self, cache_client):
        """key_prefix를 사용한 캐싱 데코레이터 테스트"""

        @cache_client.cached(ttl=60, key_prefix="v1:")
        async def get_data(key: str) -> str:
            return f"data_{key}"

        result = await get_data("test")
        assert result == "data_test"

        # 캐시 키가 접두사와 함께 생성되었는지 확인
        keys = await cache_client.keys("v1:*")
        assert len(keys) > 0


# ============================================================================
# Test 4: Metrics and Hit Rate
# ============================================================================


class TestMetrics:
    """메트릭 및 히트율 테스트"""

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, cache_client):
        """히트율 계산 테스트"""
        # 초기 히트율
        assert cache_client.get_hit_rate() == 0.0

        @cache_client.cached(ttl=60)
        async def sample_function(x: int) -> int:
            return x * 2

        # 3번 호출 (1 miss, 2 hits)
        await sample_function(1)
        await sample_function(1)
        await sample_function(1)

        # 히트율 확인 (2/3 = 0.666...)
        hit_rate = cache_client.get_hit_rate()
        assert hit_rate > 0.6
        assert hit_rate < 0.7

    @pytest.mark.asyncio
    async def test_prometheus_metrics(self, cache_client):
        """Prometheus 메트릭 수집 테스트"""
        from aegis_shared.cache.redis_client import CACHE_HITS, CACHE_MISSES

        # 현재 메트릭 값 저장
        initial_hits = CACHE_HITS.labels(function="prom_test_function")._value.get()
        initial_misses = CACHE_MISSES.labels(function="prom_test_function")._value.get()

        @cache_client.cached(ttl=60)
        async def prom_test_function(x: int) -> int:
            return x + 1

        # 함수 호출 (1 miss, 2 hits)
        await prom_test_function(1)
        await prom_test_function(1)
        await prom_test_function(1)

        # 메트릭 증가 확인
        final_hits = CACHE_HITS.labels(function="prom_test_function")._value.get()
        final_misses = CACHE_MISSES.labels(function="prom_test_function")._value.get()

        assert final_hits > initial_hits  # 2 hits
        assert final_misses > initial_misses  # 1 miss


# ============================================================================
# Test 5: Error Handling
# ============================================================================


class TestErrorHandling:
    """에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_get_with_invalid_json(self, cache_client, redis_client):
        """잘못된 JSON 데이터 처리 테스트"""
        # 직접 Redis에 잘못된 JSON 저장
        await redis_client.set("invalid_json", "not a json")

        # get 시도 - None 반환해야 함
        result = await cache_client.get("invalid_json")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_non_serializable_data(self, cache_client):
        """직렬화 불가능한 데이터 처리 테스트"""

        class NonSerializable:
            pass

        result = await cache_client.set("test", NonSerializable())
        assert result is False


# ============================================================================
# Test 6: Integration Test
# ============================================================================


async def test_cache_workflow_integration(cache_client):
    """캐시 워크플로우 통합 테스트"""

    # 1. 데이터 캐싱
    await cache_client.set("user:100", {"name": "Alice", "age": 25})
    await cache_client.set("user:101", {"name": "Bob", "age": 30})
    await cache_client.set("product:1", {"name": "Book"})

    # 2. 데이터 조회
    user = await cache_client.get("user:100")
    assert user["name"] == "Alice"

    # 3. 패턴 조회
    user_keys = await cache_client.keys("user:*")
    assert len(user_keys) == 2

    # 4. 특정 패턴 무효화
    deleted = await cache_client.delete_pattern("user:*")
    assert deleted == 2

    # 5. 무효화 확인
    assert await cache_client.get("user:100") is None
    assert await cache_client.get("product:1") is not None

    # 6. 데코레이터 사용
    @cache_client.cached(ttl=60)
    async def compute(a: int, b: int) -> int:
        return a + b

    result1 = await compute(5, 3)
    result2 = await compute(5, 3)

    assert result1 == 8
    assert result2 == 8
    assert cache_client.get_hit_rate() > 0
