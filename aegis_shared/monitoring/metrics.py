"""
메트릭 수집기

Prometheus 메트릭 수집 기능을 제공합니다.
"""

import time
import functools
from typing import Dict, Any, Callable
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

def track_metrics(metric_name: str, labels: Dict[str, str] = None):
    """메트릭 추적 데코레이터"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 메트릭 수집기 인스턴스 가져오기 (전역 또는 인자에서)
            metrics = getattr(args[0], 'metrics', None) if args else None
            if not metrics:
                # 기본 메트릭 수집기 생성
                metrics = MetricsCollector()
            
            try:
                result = await func(*args, **kwargs)
                metrics.increment_counter(f"{metric_name}_total", {**(labels or {}), "status": "success"})
                return result
            except Exception as e:
                metrics.increment_counter(f"{metric_name}_total", {**(labels or {}), "status": "error"})
                raise
            finally:
                duration = time.time() - start_time
                metrics.observe_histogram(f"{metric_name}_duration_seconds", duration, labels)
        
        return wrapper
    return decorator

class MetricsCollector:
    """메트릭 수집기"""
    
    def __init__(self):
        """메트릭 수집기 초기화"""
        self.counters: Dict[str, int] = {}
        self.histograms: Dict[str, list] = {}
        self.gauges: Dict[str, float] = {}
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None) -> None:
        """
        카운터 메트릭 증가
        
        Args:
            name: 메트릭 이름
            labels: 메트릭 라벨
        """
        key = f"{name}_{hash(str(labels) if labels else '')}"
        self.counters[key] = self.counters.get(key, 0) + 1
        logger.debug(f"Counter incremented: {name}", labels=labels)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        히스토그램 메트릭 관찰
        
        Args:
            name: 메트릭 이름
            value: 관찰값
            labels: 메트릭 라벨
        """
        key = f"{name}_{hash(str(labels) if labels else '')}"
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        logger.debug(f"Histogram observed: {name}", value=value, labels=labels)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        게이지 메트릭 설정
        
        Args:
            name: 메트릭 이름
            value: 설정값
            labels: 메트릭 라벨
        """
        key = f"{name}_{hash(str(labels) if labels else '')}"
        self.gauges[key] = value
        logger.debug(f"Gauge set: {name}", value=value, labels=labels)
    
    def track_requests(self):
        """요청 추적 데코레이터"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    self.increment_counter("requests_total", {"status": "success"})
                    return result
                except Exception as e:
                    self.increment_counter("requests_total", {"status": "error"})
                    raise
                finally:
                    duration = time.time() - start_time
                    self.observe_histogram("request_duration_seconds", duration)
            
            return wrapper
        return decorator
    
    def track_database_queries(self):
        """데이터베이스 쿼리 추적 데코레이터"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    self.increment_counter("db_queries_total", {"status": "success"})
                    return result
                except Exception as e:
                    self.increment_counter("db_queries_total", {"status": "error"})
                    raise
                finally:
                    duration = time.time() - start_time
                    self.observe_histogram("db_query_duration_seconds", duration)
            
            return wrapper
        return decorator
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        메트릭 데이터 생성
        
        Returns:
            메트릭 데이터 딕셔너리
        """
        return {
            "counters": self.counters,
            "histograms": self.histograms,
            "gauges": self.gauges
        }

# PrometheusMetrics는 MetricsCollector의 별칭
PrometheusMetrics = MetricsCollector