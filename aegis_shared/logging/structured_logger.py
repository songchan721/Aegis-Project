"""
구조화된 로깅 시스템

JSON 형식의 구조화된 로그를 생성하고 컨텍스트 정보를 자동으로 추가합니다.
"""

import logging
import json
from datetime import datetime
from contextvars import ContextVar
from typing import Optional, Dict, Any

# 컨텍스트 변수
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
service_name_var: ContextVar[Optional[str]] = ContextVar('service_name', default=None)

class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 포맷팅"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "service": service_name_var.get(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
        }
        
        # 추가 필드들
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # None 값 제거
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        return json.dumps(log_data, ensure_ascii=False)

def configure_logging(service_name: str, log_level: str = "INFO") -> None:
    """로깅 시스템 설정"""
    service_name_var.set(service_name)
    
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)

def add_context(**kwargs) -> None:
    """로깅 컨텍스트 추가"""
    for key, value in kwargs.items():
        if key == 'request_id':
            request_id_var.set(value)
        elif key == 'user_id':
            user_id_var.set(value)
        elif key == 'service_name':
            service_name_var.set(value)

class ContextLogger:
    """컨텍스트 정보를 자동으로 포함하는 로거 래퍼"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _log_with_context(self, level: int, msg: str, *args, **kwargs):
        """컨텍스트 정보와 함께 로그 기록"""
        extra_fields = {}
        
        # kwargs에서 추가 필드 추출
        for key, value in list(kwargs.items()):
            if not key.startswith('_'):
                extra_fields[key] = value
                del kwargs[key]
        
        # extra_fields를 record에 추가
        if extra_fields:
            kwargs['extra'] = {'extra_fields': extra_fields}
        
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)

# 기본 로거를 ContextLogger로 래핑하는 함수 오버라이드
_original_get_logger = get_logger

def get_logger(name: str) -> ContextLogger:
    """컨텍스트 로거 인스턴스 반환"""
    logger = _original_get_logger(name)
    return ContextLogger(logger)