import asyncio
import functools
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional

# 분산 추적을 위한 컨텍스트 변수
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class Span:
    """추적 스팬"""

    def __init__(self, name: str, trace_id: str, span_id: str):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.attributes: Dict[str, Any] = {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None

    def set_attribute(self, key: str, value: Any):
        """스팬에 속성 설정"""
        self.attributes[key] = value

    def finish(self):
        """스팬 종료"""
        self.end_time = time.time()

    def duration(self) -> Optional[float]:
        """스팬 지속 시간"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class TracingManager:
    """분산 추적 관리자"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.current_span: Optional[Span] = None

    def create_span(self, name: str):
        """스팬 생성 (context manager)"""
        return SpanContext(self, name)

    def start_trace(self, operation_name: str) -> str:
        """새로운 추적 시작"""
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        trace_id_var.set(trace_id)
        span_id_var.set(span_id)

        return trace_id

    def get_trace_id(self) -> Optional[str]:
        """현재 추적 ID 조회"""
        return trace_id_var.get()

    def get_span_id(self) -> Optional[str]:
        """현재 스팬 ID 조회"""
        return span_id_var.get()

    def get_current_trace_id(self) -> Optional[str]:
        """현재 추적 ID 조회 (별칭)"""
        return trace_id_var.get()

    def add_tag(self, key: str, value: Any):
        """추적에 태그 추가 (로깅용)"""
        if self.current_span:
            self.current_span.set_attribute(key, value)

    def finish_trace(self):
        """추적 종료"""
        trace_id_var.set(None)
        span_id_var.set(None)

    def trace_function(self, name: str):
        """함수 추적 데코레이터"""

        def decorator(func: Callable):
            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    with self.create_span(name):
                        return await func(*args, **kwargs)

                return async_wrapper
            else:

                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    with self.create_span(name):
                        return func(*args, **kwargs)

                return wrapper

        return decorator

    def inject_trace_context(self, headers: Dict[str, str]):
        """추적 컨텍스트를 헤더에 주입"""
        trace_id = self.get_trace_id()
        span_id = self.get_span_id()

        if trace_id and span_id:
            # W3C Trace Context format
            trace_part = trace_id.replace("-", "")[:32]
            span_part = span_id.replace("-", "")[:16]
            headers["traceparent"] = f"00-{trace_part}-{span_part}-01"

    def extract_trace_context(
        self, headers: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """헤더에서 추적 컨텍스트 추출"""
        traceparent = headers.get("traceparent")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 3:
                return {"trace_id": parts[1], "span_id": parts[2]}
        return None


class SpanContext:
    """스팬 컨텍스트 매니저"""

    def __init__(self, manager: TracingManager, name: str):
        self.manager = manager
        self.name = name
        self.span: Optional[Span] = None

    def __enter__(self):
        # 새로운 trace ID와 span ID 생성
        trace_id = trace_id_var.get() or str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        trace_id_var.set(trace_id)
        span_id_var.set(span_id)

        self.span = Span(self.name, trace_id, span_id)
        self.manager.current_span = self.span

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            self.span.finish()
        self.manager.current_span = None
        return False


def configure_tracing(service_name: str) -> TracingManager:
    """추적 설정"""
    return TracingManager(service_name)
