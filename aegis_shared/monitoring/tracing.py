from typing import Optional, Dict, Any
import uuid
import time
from contextvars import ContextVar

# 분산 추적을 위한 컨텍스트 변수
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)

class TracingManager:
    """분산 추적 관리자"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
    
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
    
    def add_tag(self, key: str, value: Any):
        """추적에 태그 추가 (로깅용)"""
        # 실제 구현에서는 로깅 시스템과 연동
        pass
    
    def finish_trace(self):
        """추적 종료"""
        trace_id_var.set(None)
        span_id_var.set(None)

def configure_tracing(service_name: str) -> TracingManager:
    """추적 설정"""
    return TracingManager(service_name)
