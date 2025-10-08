#!/usr/bin/env python3
"""
Aegis Shared Library 성능 벤치마크 테스트

이 스크립트는 aegis-shared 라이브러리의 주요 컴포넌트들의 성능을 측정합니다.
"""

import asyncio
import time
import statistics
import psutil
import gc
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager
import json

# Aegis Shared Library imports
from aegis_shared.database import DatabaseManager, BaseRepository
from aegis_shared.cache import CacheClient
from aegis_shared.auth import JWTHandler
from aegis_shared.logging import configure_logging, get_logger
from aegis_shared.messaging import EventPublisher
from aegis_shared.monitoring import MetricsCollector


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    ops_per_second: float
    memory_usage_mb: float
    cpu_percent: float


class PerformanceBenchmark:
    """성능 벤치마크 테스트"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.results: List[BenchmarkResult] = []
        
        # 테스트 설정
        self.iterations = 1000
        self.warmup_iterations = 100
        
        # 컴포넌트 초기화
        self.db_manager = None
        self.cache_client = None
        self.jwt_handler = None
        self.event_publisher = None
        self.metrics_collector = None
    
    async def setup(self):
        """테스트 환경 설정"""
        self.logger.info("Setting up performance benchmark environment")
        
        # 데이터베이스 (SQLite 메모리 DB 사용)
        self.db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
        
        # 캐시 (Mock Redis 사용)
        from unittest.mock import AsyncMock
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        self.cache_client = CacheClient(redis_client=mock_redis)
        
        # JWT 핸들러
        self.jwt_handler = JWTHandler(secret_key="benchmark-secret-key")
        
        # 이벤트 발행자 (Mock Kafka 사용)
        mock_producer = AsyncMock()
        self.event_publisher = EventPublisher(kafka_producer=mock_producer)
        
        # 메트릭 수집기
        self.metrics_collector = MetricsCollector()
        
        self.logger.info("Benchmark environment setup complete")
    
    async def teardown(self):
        """테스트 환경 정리"""
        if self.db_manager:
            await self.db_manager.close()
    
    @asynccontextmanager
    async def measure_performance(self, name: str, iterations: int = None):
        """성능 측정 컨텍스트 매니저"""
        if iterations is None:
            iterations = self.iterations
        
        # 메모리 사용량 측정 시작
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()
        
        # 가비지 컬렉션
        gc.collect()
        
        times = []
        
        class PerformanceContext:
            def __init__(self):
                self.iteration_times = []
            
            async def run_iteration(self, func: Callable):
                """단일 반복 실행"""
                start_time = time.perf_counter()
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
                end_time = time.perf_counter()
                self.iteration_times.append(end_time - start_time)
        
        context = PerformanceContext()
        
        try:
            yield context
            
            # 결과 계산
            if context.iteration_times:
                total_time = sum(context.iteration_times)
                avg_time = statistics.mean(context.iteration_times)
                min_time = min(context.iteration_times)
                max_time = max(context.iteration_times)
                ops_per_second = len(context.iteration_times) / total_time if total_time > 0 else 0
                
                # 메모리 사용량 측정 종료
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                end_cpu = process.cpu_percent()
                
                result = BenchmarkResult(
                    name=name,
                    iterations=len(context.iteration_times),
                    total_time=total_time,
                    avg_time=avg_time,
                    min_time=min_time,
                    max_time=max_time,
                    ops_per_second=ops_per_second,
                    memory_usage_mb=end_memory - start_memory,
                    cpu_percent=end_cpu - start_cpu
                )
                
                self.results.append(result)
                self.logger.info(f"Benchmark '{name}' completed", 
                               ops_per_second=ops_per_second,
                               avg_time_ms=avg_time * 1000)
        
        except Exception as e:
            self.logger.error(f"Benchmark '{name}' failed", error=str(e))
            raise
    
    async def benchmark_jwt_operations(self):
        """JWT 작업 성능 테스트"""
        self.logger.info("Starting JWT operations benchmark")
        
        # JWT 토큰 생성 벤치마크
        async with self.measure_performance("JWT Token Creation") as ctx:
            user_data = {"user_id": "test-user", "email": "test@example.com"}
            
            for _ in range(self.iterations):
                await ctx.run_iteration(
                    lambda: self.jwt_handler.create_access_token(user_data)
                )
        
        # JWT 토큰 검증 벤치마크
        token = self.jwt_handler.create_access_token({"user_id": "test-user"})
        
        async with self.measure_performance("JWT Token Verification") as ctx:
            for _ in range(self.iterations):
                await ctx.run_iteration(
                    lambda: self.jwt_handler.verify_token(token)
                )
    
    async def benchmark_cache_operations(self):
        """캐시 작업 성능 테스트"""
        self.logger.info("Starting cache operations benchmark")
        
        # 캐시 SET 작업 벤치마크
        async with self.measure_performance("Cache SET Operations") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda i=i: self.cache_client.set(f"key_{i}", f"value_{i}", ttl=300)
                )
        
        # 캐시 GET 작업 벤치마크
        async with self.measure_performance("Cache GET Operations") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda i=i: self.cache_client.get(f"key_{i}")
                )
        
        # 캐시 DELETE 작업 벤치마크
        async with self.measure_performance("Cache DELETE Operations") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda i=i: self.cache_client.delete(f"key_{i}")
                )
    
    async def benchmark_database_operations(self):
        """데이터베이스 작업 성능 테스트"""
        self.logger.info("Starting database operations benchmark")
        
        # 테스트용 모델 정의
        from sqlalchemy import Column, Integer, String, create_engine
        from sqlalchemy.orm import declarative_base
        
        Base = declarative_base()
        
        class TestModel(Base):
            __tablename__ = "test_model"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))
            email = Column(String(255))
        
        # 테이블 생성
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        
        # Repository 생성
        class TestRepository(BaseRepository[TestModel]):
            pass
        
        # 데이터베이스 생성 작업 벤치마크
        async with self.measure_performance("Database CREATE Operations") as ctx:
            async with self.db_manager.session() as session:
                repo = TestRepository(session, TestModel)
                
                for i in range(min(self.iterations, 100)):  # DB 작업은 적은 수로 제한
                    entity = TestModel(name=f"test_{i}", email=f"test_{i}@example.com")
                    await ctx.run_iteration(
                        lambda e=entity: repo.create(e)
                    )
        
        # 데이터베이스 조회 작업 벤치마크
        async with self.measure_performance("Database READ Operations") as ctx:
            async with self.db_manager.session() as session:
                repo = TestRepository(session, TestModel)
                
                for i in range(min(self.iterations, 100)):
                    await ctx.run_iteration(
                        lambda i=i: repo.get_by_id(i + 1)
                    )
    
    async def benchmark_event_publishing(self):
        """이벤트 발행 성능 테스트"""
        self.logger.info("Starting event publishing benchmark")
        
        async with self.measure_performance("Event Publishing") as ctx:
            for i in range(self.iterations):
                event_data = {
                    "event_id": f"event_{i}",
                    "timestamp": time.time(),
                    "data": {"key": f"value_{i}"}
                }
                
                await ctx.run_iteration(
                    lambda data=event_data: self.event_publisher.publish(
                        topic="benchmark-topic",
                        event_type="benchmark.event",
                        data=data
                    )
                )
    
    async def benchmark_metrics_collection(self):
        """메트릭 수집 성능 테스트"""
        self.logger.info("Starting metrics collection benchmark")
        
        # Counter 메트릭 벤치마크
        async with self.measure_performance("Metrics Counter Operations") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda: self.metrics_collector.increment_counter(
                        "benchmark_counter",
                        labels={"test": "benchmark"}
                    )
                )
        
        # Histogram 메트릭 벤치마크
        async with self.measure_performance("Metrics Histogram Operations") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda i=i: self.metrics_collector.observe_histogram(
                        "benchmark_histogram",
                        value=i * 0.001,
                        labels={"test": "benchmark"}
                    )
                )
        
        # Gauge 메트릭 벤치마크
        async with self.measure_performance("Metrics Gauge Operations") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda i=i: self.metrics_collector.set_gauge(
                        "benchmark_gauge",
                        value=i,
                        labels={"test": "benchmark"}
                    )
                )
    
    async def benchmark_logging_operations(self):
        """로깅 작업 성능 테스트"""
        self.logger.info("Starting logging operations benchmark")
        
        # 구조화된 로깅 벤치마크
        async with self.measure_performance("Structured Logging") as ctx:
            for i in range(self.iterations):
                await ctx.run_iteration(
                    lambda i=i: self.logger.info(
                        "Benchmark log message",
                        iteration=i,
                        test_data=f"data_{i}",
                        timestamp=time.time()
                    )
                )
    
    async def run_all_benchmarks(self):
        """모든 벤치마크 실행"""
        self.logger.info("Starting comprehensive performance benchmark")
        
        await self.setup()
        
        try:
            # 각 벤치마크 실행
            await self.benchmark_jwt_operations()
            await self.benchmark_cache_operations()
            await self.benchmark_database_operations()
            await self.benchmark_event_publishing()
            await self.benchmark_metrics_collection()
            await self.benchmark_logging_operations()
            
        finally:
            await self.teardown()
        
        self.logger.info("All benchmarks completed")
    
    def generate_report(self) -> Dict[str, Any]:
        """벤치마크 결과 보고서 생성"""
        if not self.results:
            return {"error": "No benchmark results available"}
        
        report = {
            "summary": {
                "total_benchmarks": len(self.results),
                "total_operations": sum(r.iterations for r in self.results),
                "total_time": sum(r.total_time for r in self.results),
                "average_ops_per_second": statistics.mean([r.ops_per_second for r in self.results]),
                "total_memory_usage_mb": sum(r.memory_usage_mb for r in self.results)
            },
            "benchmarks": []
        }
        
        for result in self.results:
            benchmark_data = {
                "name": result.name,
                "iterations": result.iterations,
                "performance": {
                    "total_time_seconds": round(result.total_time, 4),
                    "average_time_ms": round(result.avg_time * 1000, 4),
                    "min_time_ms": round(result.min_time * 1000, 4),
                    "max_time_ms": round(result.max_time * 1000, 4),
                    "operations_per_second": round(result.ops_per_second, 2)
                },
                "resources": {
                    "memory_usage_mb": round(result.memory_usage_mb, 2),
                    "cpu_percent": round(result.cpu_percent, 2)
                }
            }
            report["benchmarks"].append(benchmark_data)
        
        # 성능 등급 계산
        report["performance_grade"] = self._calculate_performance_grade()
        
        return report
    
    def _calculate_performance_grade(self) -> str:
        """성능 등급 계산"""
        if not self.results:
            return "N/A"
        
        avg_ops_per_second = statistics.mean([r.ops_per_second for r in self.results])
        
        if avg_ops_per_second >= 10000:
            return "A+"
        elif avg_ops_per_second >= 5000:
            return "A"
        elif avg_ops_per_second >= 1000:
            return "B"
        elif avg_ops_per_second >= 500:
            return "C"
        else:
            return "D"
    
    def save_report(self, filename: str = "benchmark_report.json"):
        """보고서를 파일로 저장"""
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Benchmark report saved to {filename}")
    
    def print_summary(self):
        """벤치마크 결과 요약 출력"""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("AEGIS SHARED LIBRARY PERFORMANCE BENCHMARK REPORT")
        print("="*80)
        
        summary = report["summary"]
        print(f"Total Benchmarks: {summary['total_benchmarks']}")
        print(f"Total Operations: {summary['total_operations']:,}")
        print(f"Total Time: {summary['total_time']:.2f} seconds")
        print(f"Average Ops/Second: {summary['average_ops_per_second']:.2f}")
        print(f"Total Memory Usage: {summary['total_memory_usage_mb']:.2f} MB")
        print(f"Performance Grade: {report['performance_grade']}")
        
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)
        
        for benchmark in report["benchmarks"]:
            print(f"\n{benchmark['name']}:")
            print(f"  Operations: {benchmark['iterations']:,}")
            print(f"  Avg Time: {benchmark['performance']['average_time_ms']:.2f} ms")
            print(f"  Ops/Second: {benchmark['performance']['operations_per_second']:.2f}")
            print(f"  Memory: {benchmark['resources']['memory_usage_mb']:.2f} MB")
        
        print("\n" + "="*80)


async def main():
    """메인 함수"""
    # 로깅 설정
    configure_logging(service_name="benchmark", log_level="INFO")
    
    # 벤치마크 실행
    benchmark = PerformanceBenchmark()
    
    print("Starting Aegis Shared Library Performance Benchmark...")
    print("This may take a few minutes to complete.\n")
    
    start_time = time.time()
    
    try:
        await benchmark.run_all_benchmarks()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\nBenchmark completed in {total_time:.2f} seconds")
        
        # 결과 출력
        benchmark.print_summary()
        
        # 보고서 저장
        benchmark.save_report("benchmark_report.json")
        
    except Exception as e:
        print(f"Benchmark failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))