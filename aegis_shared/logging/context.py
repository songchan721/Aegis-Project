import logging
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any

# Context Variables
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
service_name_var: ContextVar[Optional[str]] = ContextVar('service_name', default=None)

class LoggingContext:
    """로깅 컨텍스트 관리"""

    @staticmethod
    def set_request_id(request_id: Optional[str] = None) -> str:
        """요청 ID 설정"""
        if request_id is None:
            request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        return request_id

    @staticmethod
    def get_request_id() -> Optional[str]:
        """요청 ID 조회"""
        return request_id_var.get()

    @staticmethod
    def set_user_id(user_id: Optional[str]) -> None:
        """사용자 ID 설정"""
        user_id_var.set(user_id)

    @staticmethod
    def get_user_id() -> Optional[str]:
        """사용자 ID 조회"""
        return user_id_var.get()

    @staticmethod
    def set_session_id(session_id: Optional[str]) -> None:
        """세션 ID 설정"""
        session_id_var.set(session_id)

    @staticmethod
    def get_session_id() -> Optional[str]:
        """세션 ID 조회"""
        return session_id_var.get()

    @staticmethod
    def set_trace_id(trace_id: Optional[str]) -> None:
        """추적 ID 설정"""
        trace_id_var.set(trace_id)

    @staticmethod
    def get_trace_id() -> Optional[str]:
        """추적 ID 조회"""
        return trace_id_var.get()

    @staticmethod
    def set_service_name(service_name: Optional[str]) -> None:
        """서비스 이름 설정"""
        service_name_var.set(service_name)

    @staticmethod
    def get_service_name() -> Optional[str]:
        """서비스 이름 조회"""
        return service_name_var.get()

    @staticmethod
    def get_all_context() -> Dict[str, Any]:
        """모든 컨텍스트 정보 조회"""
        return {
            'request_id': request_id_var.get(),
            'user_id': user_id_var.get(),
            'session_id': session_id_var.get(),
            'trace_id': trace_id_var.get(),
            'service_name': service_name_var.get()
        }

    @staticmethod
    def clear_context() -> None:
        """모든 컨텍스트 초기화"""
        request_id_var.set(None)
        user_id_var.set(None)
        session_id_var.set(None)
        trace_id_var.set(None)
        service_name_var.set(None)

class ContextFilter(logging.Filter):
    """로그 레코드에 컨텍스트 정보 추가"""

    def filter(self, record: logging.LogRecord) -> bool:
        # 요청 ID 추가
        if not hasattr(record, 'request_id'):
            record.request_id = request_id_var.get()

        # 사용자 ID 추가
        if not hasattr(record, 'user_id'):
            record.user_id = user_id_var.get()

        # 세션 ID 추가
        if not hasattr(record, 'session_id'):
            record.session_id = session_id_var.get()

        # 추적 ID 추가
        if not hasattr(record, 'trace_id'):
            record.trace_id = trace_id_var.get()

        # 서비스 이름 추가
        if not hasattr(record, 'service_name'):
            record.service_name = service_name_var.get()

        return True

def add_context(**kwargs) -> None:
    """로그 컨텍스트 추가"""
    for key, value in kwargs.items():
        if key == 'request_id':
            LoggingContext.set_request_id(value)
        elif key == 'user_id':
            LoggingContext.set_user_id(value)
        elif key == 'session_id':
            LoggingContext.set_session_id(value)
        elif key == 'trace_id':
            LoggingContext.set_trace_id(value)
        elif key == 'service_name':
            LoggingContext.set_service_name(value)

def get_context() -> Dict[str, Any]:
    """현재 컨텍스트 반환"""
    return {
        'request_id': request_id_var.get(),
        'user_id': user_id_var.get(),
        'session_id': session_id_var.get(),
        'trace_id': trace_id_var.get(),
        'service_name': service_name_var.get(),
    }

def clear_context() -> None:
    """컨텍스트 초기화"""
    request_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)
    trace_id_var.set(None)
    service_name_var.set(None)

class StructuredLogger:
    """구조화된 로깅을 지원하는 로거 래퍼"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        # ContextFilter 추가 (중복 방지)
        if not any(isinstance(f, ContextFilter) for f in logger.filters):
            logger.addFilter(ContextFilter())
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """로그 메시지 처리"""
        # kwargs에서 extra 정보 추출
        extra = {}
        for key, value in kwargs.items():
            if key not in ['exc_info', 'stack_info', 'stacklevel']:
                extra[key] = value
        
        # extra가 있으면 추가
        if extra:
            self.logger._log(level, msg, args, extra=extra)
        else:
            self.logger._log(level, msg, args)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """예외 정보와 함께 에러 로그 기록"""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, msg, *args, **kwargs)

def get_logger(name: str) -> StructuredLogger:
    """컨텍스트 정보를 포함한 로거 생성"""
    logger = logging.getLogger(name)
    return StructuredLogger(logger)
