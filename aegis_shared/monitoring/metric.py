"""
메트릭 수집기

Prometheus 메트릭 수집 기능을 제공합니다.
"""

import time
import functools
import asyncio
from typing import Dict, Any, Callable, Optional
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, generate_latest
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

def track_metrics(metric_name: str, labels: Dict[str, str] = None):
    """메트릭 추적 데코레이터 (sync/async 모두 지원)"""
    def decorator(func: Callable):
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()

                # 메트릭 수집기 인스턴스 가져오기
                metrics = getattr(args[0], 'metrics', None) if args else None
                if not metrics:
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

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()

                # 메트릭 수집기 인스턴스 가져오기
                metrics = getattr(args[0], 'metrics', None) if args else None
                if not metrics:
                    metrics = MetricsCollector()

                try:
                    result = func(*args, **kwargs)
                    metrics.increment_counter(f"{metric_name}_total", {**(labels or {}), "status": "success"})
                    return result
                except Exception as e:
                    metrics.increment_counter(f"{metric_name}_total", {**(labels or {}), "status": "error"})
                    raise
                finally:
                    duration = time.time() - start_time
                    metrics.observe_histogram(f"{metric_name}_duration_seconds", duration, labels)

            return sync_wrapper
    return decorator

class MetricsCollector:
    """메트릭 수집기 (Prometheus 통합)"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        메트릭 수집기 초기화

        Args:
            registry: Prometheus registry
        """
        self.registry = registry or CollectorRegistry()
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._gauges: Dict[str, Gauge] = {}

    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1) -> None:
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
        """요청 추적 데코레이터 (sync/async 모두 지원)"""
        def decorator(func: Callable):
            is_async = asyncio.iscoroutinefunction(func)

            if is_async:
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
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

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()

                    try:
                        result = func(*args, **kwargs)
                        self.increment_counter("requests_total", {"status": "success"})
                        return result
                    except Exception as e:
                        self.increment_counter("requests_total", {"status": "error"})
                        raise
                    finally:
                        duration = time.time() - start_time
                        self.observe_histogram("request_duration_seconds", duration)

                return sync_wrapper
        return decorator

    def track_database_queries(self):
        """데이터베이스 쿼리 추적 데코레이터 (sync/async 모두 지원)"""
        def decorator(func: Callable):
            is_async = asyncio.iscoroutinefunction(func)

            if is_async:
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
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

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()

                    try:
                        result = func(*args, **kwargs)
                        self.increment_counter("db_queries_total", {"status": "success"})
                        return result
                    except Exception as e:
                        self.increment_counter("db_queries_total", {"status": "error"})
                        raise
                    finally:
                        duration = time.time() - start_time
                        self.observe_histogram("db_query_duration_seconds", duration)

                return sync_wrapper
        return decorator

    def track_custom(self, metric_name: str, labels: list[str] = None):
        """
        커스텀 메트릭 추적 데코레이터

        Args:
            metric_name: 메트릭 이름
            labels: 라벨 이름 리스트 (함수의 kwargs에서 자동 추출)
        """
        def decorator(func: Callable):
            is_async = asyncio.iscoroutinefunction(func)

            if is_async:
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()

                    # 라벨 값 추출
                    label_values = {}
                    if labels:
                        for label_name in labels:
                            if label_name in kwargs:
                                label_values[label_name] = str(kwargs[label_name])

                    try:
                        result = await func(*args, **kwargs)
                        self.increment_counter(f"{metric_name}_total", {**label_values, "status": "success"})
                        return result
                    except Exception as e:
                        self.increment_counter(f"{metric_name}_total", {**label_values, "status": "error"})
                        raise
                    finally:
                        duration = time.time() - start_time
                        self.observe_histogram(f"{metric_name}_duration_seconds", duration, label_values)

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()

                    # 라벨 값 추출
                    label_values = {}
                    if labels:
                        for label_name in labels:
                            if label_name in kwargs:
                                label_values[label_name] = str(kwargs[label_name])

                    try:
                        result = func(*args, **kwargs)
                        self.increment_counter(f"{metric_name}_total", {**label_values, "status": "success"})
                        return result
                    except Exception as e:
                        self.increment_counter(f"{metric_name}_total", {**label_values, "status": "error"})
                        raise
                    finally:
                        duration = time.time() - start_time
                        self.observe_histogram(f"{metric_name}_duration_seconds", duration, label_values)

                return sync_wrapper
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


class PrometheusMetrics:
    """Prometheus 메트릭 클래스 (실제 Prometheus 통합)"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Prometheus 메트릭 초기화

        Args:
            registry: Prometheus registry
        """
        self.registry = registry or CollectorRegistry()
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._gauges: Dict[str, Gauge] = {}

    def increment_counter(self, name: str, labels: Dict[str, Any] = None, value: float = 1) -> None:
        """
        카운터 증가

        Args:
            name: 메트릭 이름
            labels: 라벨 딕셔너리
            value: 증가할 값
        """
        if name not in self._counters:
            label_names = list(labels.keys()) if labels else []
            self._counters[name] = Counter(
                name,
                f'Counter metric: {name}',
                labelnames=label_names,
                registry=self.registry
            )

        if labels:
            self._counters[name].labels(**labels).inc(value)
        else:
            self._counters[name].inc(value)

    def observe_histogram(self, name: str, value: float, labels: Dict[str, Any] = None) -> None:
        """
        히스토그램 관찰

        Args:
            name: 메트릭 이름
            value: 관찰값
            labels: 라벨 딕셔너리
        """
        if name not in self._histograms:
            label_names = list(labels.keys()) if labels else []
            self._histograms[name] = Histogram(
                name,
                f'Histogram metric: {name}',
                labelnames=label_names,
                registry=self.registry
            )

        if labels:
            self._histograms[name].labels(**labels).observe(value)
        else:
            self._histograms[name].observe(value)

    def set_gauge(self, name: str, labels: Dict[str, Any] = None, value: float = 0) -> None:
        """
        게이지 설정

        Args:
            name: 메트릭 이름
            labels: 라벨 딕셔너리
            value: 설정할 값
        """
        if name not in self._gauges:
            label_names = list(labels.keys()) if labels else []
            self._gauges[name] = Gauge(
                name,
                f'Gauge metric: {name}',
                labelnames=label_names,
                registry=self.registry
            )

        if labels:
            self._gauges[name].labels(**labels).set(value)
        else:
            self._gauges[name].set(value)

    def get_metrics_output(self) -> str:
        """
        Prometheus 메트릭 출력 생성

        Returns:
            Prometheus 텍스트 형식의 메트릭
        """
        return generate_latest(self.registry).decode('utf-8')