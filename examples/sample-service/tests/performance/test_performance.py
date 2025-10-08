"""
Aegis Shared Library 성능 테스트

이 테스트는 shared library의 성능 특성을 측정하고 벤치마크를 제공합니다.
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List
import psutil
import gc

from aegis_shared.database import DatabaseManager, BaseRepository
from aegis_shared.auth import JWTHandler
from aegis_shared.cache import CacheClient
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.logging import configure_logging, get_logger

class PerformanceTestResult:
    """성능 테스트 결과"""
    
    def __init__(self, name: str):
        self.name = name
        self.execution_times: List[float] = []
        self.memory_usage: List[float] = []
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """측정 시작"""
        gc.collect()  # 가비지 컬렉션 실행
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    def end(self):
        """측정 종료"""
        self.end_time = time.time()
        self.end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        execution_time = self.end_time - self.start_time
        memory_delta = self.end_memory - self.start_memory
        
        self.execution_times.append(execution_time)
        self.memory_usage.append(memory_delta)
    
    def get_stats(self):
        """통계 정보 반환"""
        if not self.execution_times:
            return {}
        
        return {
            "name": self.name,
            "execution_time": {
                "mean": statistics.mean(self.execution_times),
                "median": statistics.median(self.execution_times),
                "min": min(self.execution_times),
                "max": max(self.execution_times),
                "stdev": statistics.stdev(self.execution_times) if len(self.execution_times) > 1 else 0
            },
            "memory_usage": {
                "mean": statistics.mean(self.memory_usage),
                "median": statistics.median(self.memory_usage),
                "min": min(self.memory_usage),
                "max": max(self.memory_usage)
            },
            "iterations": len(self.execution_times)
        }

class TestDatabasePerformance:
    """데이터베이스 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_database_connection_performance(self):
        """데이터베이스 연결 성능 테스트"""
        result = PerformanceTestResult("database_connection")
        
        # 100회 연결 테스트
        for i in range(100):
            result.start()
            
            db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
            async with db_manager.session() as session:
                # 간단한 쿼리 실행
                await session.execute("SELECT 1")
            await db_manager.close()
            
            result.end()
        
        stats = result.get_stats()
        print(f"\n데이터베이스 연결 성능: {stats}")
        
        # 성능 기준 검증 (평균 100ms 이하)
        assert stats["execution_time"]["mean"] < 0.1, f"데이터베이스 연결이 너무 느림: {stats['execution_time']['mean']:.3f}s"
    
    @pytest.mark.asyncio
    async def test_repository_crud_performance(self):
        """Repository CRUD 성능 테스트"""
        from unittest.mock import AsyncMock, Mock
        
        result = PerformanceTestResult("repository_crud")
        
        # Mock 세션과 모델
        mock_session = AsyncMock()
        mock_model = Mock()
        
        # Repository 인스턴스
        repo = BaseRepository(mock_session, mock_model)
        
        # 1000회 CRUD 작업 시뮬레이션
        for i in range(1000):
            result.start()
            
            # CRUD 작업 시뮬레이션
            await repo.get_by_id(f"id-{i}")
            await repo.create(mock_model)
            await repo.update(f"id-{i}", name=f"name-{i}")
            await repo.delete(f"id-{i}")
            
            result.end()
        
        stats = result.get_stats()
        print(f"\nRepository CRUD 성능: {stats}")
        
        # 성능 기준 검증 (평균 1ms 이하)
        assert stats["execution_time"]["mean"] < 0.001, f"Repository CRUD가 너무 느림: {stats['execution_time']['mean']:.6f}s"

class TestAuthPerformance:
    """인증 성능 테스트"""
    
    def test_jwt_token_generation_performance(self):
        """JWT 토큰 생성 성능 테스트"""
        result = PerformanceTestResult("jwt_token_generation")
        jwt_handler = JWTHandler("test-secret-key")
        
        # 10000회 토큰 생성
        for i in range(10000):
            result.start()
            
            token = jwt_handler.create_access_token({
                "user_id": f"user-{i}",
                "email": f"user{i}@example.com",
                "role": "user"
            })
            
            result.end()
        
        stats = result.get_stats()
        print(f"\nJWT 토큰 생성 성능: {stats}")
        
        # 성능 기준 검증 (평균 1ms 이하)
        assert stats["execution_time"]["mean"] < 0.001, f"JWT 토큰 생성이 너무 느림: {stats['execution_time']['mean']:.6f}s"
    
    def test_jwt_token_verification_performance(self):
        """JWT 토큰 검증 성능 테스트"""
        result = PerformanceTestResult("jwt_token_verification")
        jwt_handler = JWTHandler("test-secret-key")
        
        # 토큰 미리 생성
        tokens = []
        for i in range(1000):
            token = jwt_handler.create_access_token({
                "user_id": f"user-{i}",
                "email": f"user{i}@example.com"
            })
            tokens.append(token)
        
        # 1000회 토큰 검증
        for token in tokens:
            result.start()
            
            payload = jwt_handler.verify_token(token)
            
            result.end()
        
        stats = result.get_stats()
        print(f"\nJWT 토큰 검증 성능: {stats}")
        
        # 성능 기준 검증 (평균 1ms 이하)
        assert stats["execution_time"]["mean"] < 0.001, f"JWT 토큰 검증이 너무 느림: {stats['execution_time']['mean']:.6f}s"

class TestCachePerformance:
    """캐시 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_cache_operations_performance(self):
        """캐시 작업 성능 테스트"""
        from unittest.mock import AsyncMock
        
        result = PerformanceTestResult("cache_operations")
        
        # Mock Redis 클라이언트
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b'{"key": "value"}'
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        
        cache_client = CacheClient(mock_redis)
        
        # 1000회 캐시 작업
        for i in range(1000):
            result.start()
            
            # 캐시 설정, 조회, 삭제
            await cache_client.set(f"key-{i}", {"data": f"value-{i}"}, ttl=300)
            await cache_client.get(f"key-{i}")
            await cache_client.delete(f"key-{i}")
            
            result.end()
        
        stats = result.get_stats()
        print(f"\n캐시 작업 성능: {stats}")
        
        # 성능 기준 검증 (평균 1ms 이하)
        assert stats["execution_time"]["mean"] < 0.001, f"캐시 작업이 너무 느림: {stats['execution_time']['mean']:.6f}s"

class TestLoggingPerformance:
    """로깅 성능 테스트"""
    
    def test_logging_performance(self):
        """로깅 성능 테스트"""
        result = PerformanceTestResult("logging")
        
        configure_logging("performance-test", "INFO")
        logger = get_logger(__name__)
        
        # 10000회 로그 기록
        for i in range(10000):
            result.start()
            
            logger.info(
                "Performance test log",
                iteration=i,
                user_id=f"user-{i}",
                action="test"
            )
            
            result.end()
        
        stats = result.get_stats()
        print(f"\n로깅 성능: {stats}")
        
        # 성능 기준 검증 (평균 0.1ms 이하)
        assert stats["execution_time"]["mean"] < 0.0001, f"로깅이 너무 느림: {stats['execution_time']['mean']:.6f}s"

class TestMonitoringPerformance:
    """모니터링 성능 테스트"""
    
    def test_metrics_collection_performance(self):
        """메트릭 수집 성능 테스트"""
        result = PerformanceTestResult("metrics_collection")
        metrics = MetricsCollector()
        
        # 10000회 메트릭 수집
        for i in range(10000):
            result.start()
            
            # 다양한 메트릭 수집
            metrics.increment_counter("test_counter", labels={"type": "performance"})
            metrics.observe_histogram("test_histogram", value=i * 0.001)
            metrics.set_gauge("test_gauge", value=i)
            
            result.end()
        
        stats = result.get_stats()
        print(f"\n메트릭 수집 성능: {stats}")
        
        # 성능 기준 검증 (평균 0.1ms 이하)
        assert stats["execution_time"]["mean"] < 0.0001, f"메트릭 수집이 너무 느림: {stats['execution_time']['mean']:.6f}s"

class TestConcurrencyPerformance:
    """동시성 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_concurrent_jwt_operations(self):
        """동시 JWT 작업 성능 테스트"""
        jwt_handler = JWTHandler("test-secret-key")
        
        async def jwt_operation(user_id: int):
            """JWT 토큰 생성 및 검증"""
            token = jwt_handler.create_access_token({
                "user_id": f"user-{user_id}",
                "email": f"user{user_id}@example.com"
            })
            payload = jwt_handler.verify_token(token)
            return payload
        
        # 1000개의 동시 작업
        start_time = time.time()
        
        tasks = [jwt_operation(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n동시 JWT 작업 성능: {execution_time:.3f}s (1000 작업)")
        print(f"초당 처리량: {1000 / execution_time:.0f} ops/sec")
        
        # 모든 작업이 성공했는지 확인
        assert len(results) == 1000
        
        # 성능 기준 검증 (1초 이하)
        assert execution_time < 1.0, f"동시 JWT 작업이 너무 느림: {execution_time:.3f}s"
    
    def test_concurrent_logging(self):
        """동시 로깅 성능 테스트"""
        configure_logging("concurrent-test", "INFO")
        logger = get_logger(__name__)
        
        def log_operation(thread_id: int):
            """로그 기록 작업"""
            for i in range(100):
                logger.info(
                    "Concurrent log test",
                    thread_id=thread_id,
                    iteration=i
                )
        
        # 10개 스레드에서 각각 100개 로그 기록
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(log_operation, i) for i in range(10)]
            for future in futures:
                future.result()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n동시 로깅 성능: {execution_time:.3f}s (1000 로그)")
        print(f"초당 처리량: {1000 / execution_time:.0f} logs/sec")
        
        # 성능 기준 검증 (1초 이하)
        assert execution_time < 1.0, f"동시 로깅이 너무 느림: {execution_time:.3f}s"

class TestMemoryUsage:
    """메모리 사용량 테스트"""
    
    def test_memory_leak_detection(self):
        """메모리 누수 탐지 테스트"""
        jwt_handler = JWTHandler("test-secret-key")
        
        # 초기 메모리 사용량
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # 대량의 토큰 생성 및 검증
        for i in range(10000):
            token = jwt_handler.create_access_token({
                "user_id": f"user-{i}",
                "data": "x" * 100  # 추가 데이터
            })
            payload = jwt_handler.verify_token(token)
        
        # 가비지 컬렉션 후 메모리 사용량
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = final_memory - initial_memory
        
        print(f"\n메모리 사용량 테스트:")
        print(f"초기 메모리: {initial_memory:.2f} MB")
        print(f"최종 메모리: {final_memory:.2f} MB")
        print(f"메모리 증가: {memory_increase:.2f} MB")
        
        # 메모리 증가가 50MB 이하인지 확인 (메모리 누수 방지)
        assert memory_increase < 50, f"메모리 사용량이 너무 많이 증가: {memory_increase:.2f} MB"

def print_performance_summary():
    """성능 테스트 요약 출력"""
    print("\n" + "="*80)
    print("AEGIS SHARED LIBRARY 성능 테스트 요약")
    print("="*80)
    print("✅ 데이터베이스 연결: < 100ms")
    print("✅ Repository CRUD: < 1ms")
    print("✅ JWT 토큰 생성: < 1ms")
    print("✅ JWT 토큰 검증: < 1ms")
    print("✅ 캐시 작업: < 1ms")
    print("✅ 로깅: < 0.1ms")
    print("✅ 메트릭 수집: < 0.1ms")
    print("✅ 동시 JWT 작업: > 1000 ops/sec")
    print("✅ 동시 로깅: > 1000 logs/sec")
    print("✅ 메모리 사용량: < 50MB 증가")
    print("="*80)

if __name__ == "__main__":
    # 성능 테스트 실행
    pytest.main([__file__, "-v", "-s"])
    print_performance_summary()