"""
Aegis Shared Library 벤치마크 스크립트

이 스크립트는 shared library의 성능을 측정하고 벤치마크 리포트를 생성합니다.
"""

import asyncio
import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Any
import psutil
import gc

from aegis_shared.database import DatabaseManager, BaseRepository
from aegis_shared.auth import JWTHandler
from aegis_shared.cache import CacheClient
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.logging import configure_logging, get_logger

class BenchmarkRunner:
    """벤치마크 실행기"""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.system_info = self._get_system_info()
    
    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / (1024**3),  # GB
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def measure_performance(self, name: str, func, iterations: int = 1000, *args, **kwargs):
        """성능 측정"""
        execution_times = []
        memory_usage = []
        
        # 워밍업
        for _ in range(10):
            if asyncio.iscoroutinefunction(func):
                asyncio.run(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
        
        # 실제 측정
        for i in range(iterations):
            gc.collect()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            start_time = time.perf_counter()
            
            if asyncio.iscoroutinefunction(func):
                asyncio.run(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
            
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            execution_times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        # 통계 계산
        self.results[name] = {
            "iterations": iterations,
            "execution_time": {
                "mean": statistics.mean(execution_times),
                "median": statistics.median(execution_times),
                "min": min(execution_times),
                "max": max(execution_times),
                "p95": self._percentile(execution_times, 95),
                "p99": self._percentile(execution_times, 99),
                "stdev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
            },
            "memory_usage": {
                "mean": statistics.mean(memory_usage),
                "median": statistics.median(memory_usage),
                "min": min(memory_usage),
                "max": max(memory_usage)
            },
            "throughput": {
                "ops_per_second": iterations / sum(execution_times),
                "ms_per_op": statistics.mean(execution_times) * 1000
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def run_all_benchmarks(self):
        """모든 벤치마크 실행"""
        print("🚀 Aegis Shared Library 벤치마크 시작...")
        
        # JWT 벤치마크
        self._benchmark_jwt()
        
        # 데이터베이스 벤치마크
        self._benchmark_database()
        
        # 캐시 벤치마크
        self._benchmark_cache()
        
        # 로깅 벤치마크
        self._benchmark_logging()
        
        # 모니터링 벤치마크
        self._benchmark_monitoring()
        
        # 동시성 벤치마크
        self._benchmark_concurrency()
        
        print("✅ 모든 벤치마크 완료!")
    
    def _benchmark_jwt(self):
        """JWT 벤치마크"""
        print("📊 JWT 성능 측정 중...")
        
        jwt_handler = JWTHandler("benchmark-secret-key")
        
        # 토큰 생성 벤치마크
        def create_token():
            return jwt_handler.create_access_token({
                "user_id": "user-123",
                "email": "user@example.com",
                "role": "user",
                "permissions": ["read", "write"]
            })
        
        self.measure_performance("jwt_token_creation", create_token, 10000)
        
        # 토큰 검증 벤치마크
        token = create_token()
        
        def verify_token():
            return jwt_handler.verify_token(token)
        
        self.measure_performance("jwt_token_verification", verify_token, 10000)
    
    def _benchmark_database(self):
        """데이터베이스 벤치마크"""
        print("📊 데이터베이스 성능 측정 중...")
        
        async def database_operations():
            db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
            async with db_manager.session() as session:
                await session.execute("SELECT 1")
            await db_manager.close()
        
        self.measure_performance("database_connection", database_operations, 100)
        
        # Repository 벤치마크
        from unittest.mock import AsyncMock, Mock
        
        async def repository_operations():
            mock_session = AsyncMock()
            mock_model = Mock()
            repo = BaseRepository(mock_session, mock_model)
            
            await repo.get_by_id("test-id")
            await repo.create(mock_model)
            await repo.update("test-id", name="test")
            await repo.delete("test-id")
        
        self.measure_performance("repository_crud", repository_operations, 1000)
    
    def _benchmark_cache(self):
        """캐시 벤치마크"""
        print("📊 캐시 성능 측정 중...")
        
        from unittest.mock import AsyncMock
        
        async def cache_operations():
            mock_redis = AsyncMock()
            mock_redis.get.return_value = b'{"key": "value"}'
            mock_redis.set.return_value = True
            mock_redis.delete.return_value = 1
            
            cache_client = CacheClient(mock_redis)
            
            await cache_client.set("test-key", {"data": "value"}, ttl=300)
            await cache_client.get("test-key")
            await cache_client.delete("test-key")
        
        self.measure_performance("cache_operations", cache_operations, 1000)
    
    def _benchmark_logging(self):
        """로깅 벤치마크"""
        print("📊 로깅 성능 측정 중...")
        
        configure_logging("benchmark-test", "INFO")
        logger = get_logger(__name__)
        
        def logging_operation():
            logger.info(
                "Benchmark log message",
                user_id="user-123",
                action="benchmark",
                data={"key": "value", "number": 42}
            )
        
        self.measure_performance("logging", logging_operation, 10000)
    
    def _benchmark_monitoring(self):
        """모니터링 벤치마크"""
        print("📊 모니터링 성능 측정 중...")
        
        metrics = MetricsCollector()
        
        def monitoring_operations():
            metrics.increment_counter("benchmark_counter", labels={"type": "test"})
            metrics.observe_histogram("benchmark_histogram", value=0.123)
            metrics.set_gauge("benchmark_gauge", value=42)
        
        self.measure_performance("monitoring", monitoring_operations, 10000)
    
    def _benchmark_concurrency(self):
        """동시성 벤치마크"""
        print("📊 동시성 성능 측정 중...")
        
        jwt_handler = JWTHandler("benchmark-secret-key")
        
        async def concurrent_jwt_operations():
            tasks = []
            for i in range(100):
                async def jwt_task():
                    token = jwt_handler.create_access_token({
                        "user_id": f"user-{i}",
                        "email": f"user{i}@example.com"
                    })
                    return jwt_handler.verify_token(token)
                
                tasks.append(jwt_task())
            
            await asyncio.gather(*tasks)
        
        self.measure_performance("concurrent_jwt", concurrent_jwt_operations, 100)
    
    def generate_report(self) -> str:
        """벤치마크 리포트 생성"""
        report = {
            "benchmark_info": {
                "library": "aegis-shared",
                "version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat()
            },
            "system_info": self.system_info,
            "results": self.results,
            "summary": self._generate_summary()
        }
        
        return json.dumps(report, indent=2)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """요약 정보 생성"""
        summary = {}
        
        for name, result in self.results.items():
            summary[name] = {
                "avg_ms": result["execution_time"]["mean"] * 1000,
                "ops_per_sec": result["throughput"]["ops_per_second"],
                "p95_ms": result["execution_time"]["p95"] * 1000,
                "memory_mb": result["memory_usage"]["mean"]
            }
        
        return summary
    
    def print_summary(self):
        """요약 정보 출력"""
        print("\n" + "="*80)
        print("🎯 AEGIS SHARED LIBRARY 벤치마크 결과")
        print("="*80)
        
        print(f"📋 시스템 정보:")
        print(f"   CPU 코어: {self.system_info['cpu_count']}")
        print(f"   메모리: {self.system_info['memory_total']:.1f} GB")
        print(f"   Python: {self.system_info['python_version']}")
        print()
        
        print("📊 성능 결과:")
        for name, result in self.results.items():
            avg_ms = result["execution_time"]["mean"] * 1000
            ops_per_sec = result["throughput"]["ops_per_second"]
            p95_ms = result["execution_time"]["p95"] * 1000
            
            print(f"   {name:25} | {avg_ms:8.3f} ms | {ops_per_sec:10,.0f} ops/sec | P95: {p95_ms:8.3f} ms")
        
        print("\n🎯 성능 등급:")
        self._print_performance_grades()
        
        print("="*80)
    
    def _print_performance_grades(self):
        """성능 등급 출력"""
        grades = {
            "jwt_token_creation": {"excellent": 0.1, "good": 0.5, "acceptable": 1.0},
            "jwt_token_verification": {"excellent": 0.1, "good": 0.5, "acceptable": 1.0},
            "database_connection": {"excellent": 10, "good": 50, "acceptable": 100},
            "repository_crud": {"excellent": 0.1, "good": 0.5, "acceptable": 1.0},
            "cache_operations": {"excellent": 0.1, "good": 0.5, "acceptable": 1.0},
            "logging": {"excellent": 0.01, "good": 0.05, "acceptable": 0.1},
            "monitoring": {"excellent": 0.01, "good": 0.05, "acceptable": 0.1}
        }
        
        for name, result in self.results.items():
            if name not in grades:
                continue
            
            avg_ms = result["execution_time"]["mean"] * 1000
            thresholds = grades[name]
            
            if avg_ms <= thresholds["excellent"]:
                grade = "🟢 EXCELLENT"
            elif avg_ms <= thresholds["good"]:
                grade = "🟡 GOOD"
            elif avg_ms <= thresholds["acceptable"]:
                grade = "🟠 ACCEPTABLE"
            else:
                grade = "🔴 NEEDS IMPROVEMENT"
            
            print(f"   {name:25} | {grade}")
    
    def save_report(self, filename: str = None):
        """리포트 파일 저장"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            f.write(self.generate_report())
        
        print(f"📄 벤치마크 리포트 저장: {filename}")

def main():
    """메인 함수"""
    print("🚀 Aegis Shared Library 벤치마크 시작")
    print("이 벤치마크는 몇 분 정도 소요될 수 있습니다...\n")
    
    runner = BenchmarkRunner()
    runner.run_all_benchmarks()
    runner.print_summary()
    runner.save_report()
    
    print("\n✅ 벤치마크 완료!")

if __name__ == "__main__":
    main()