import logging
import json
from logging.handlers import RotatingFileHandler
from elasticsearch import Elasticsearch
from typing import Optional

def get_console_handler():
    console_handler = logging.StreamHandler()
    return console_handler

def get_file_handler(filename: str, max_bytes: int = 1024 * 1024 * 10, backup_count: int = 5):
    file_handler = RotatingFileHandler(filename, maxBytes=max_bytes, backupCount=backup_count)
    return file_handler

class StructuredFileHandler(RotatingFileHandler):
    """구조화된 로그를 파일에 기록하는 핸들러"""
    
    def __init__(self, filename: str, max_bytes: int = 1024 * 1024 * 10, backup_count: int = 5):
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count)
    
    def format(self, record):
        """로그 레코드를 JSON 형태로 포맷"""
        import time
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
            'level': record.levelname.lower(),
            'logger': record.name,
            'message': record.getMessage(),
            'event': record.getMessage(),  # event 필드 추가
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 컨텍스트 정보 추가
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        if hasattr(record, 'trace_id'):
            log_data['trace_id'] = record.trace_id
        if hasattr(record, 'service_name'):
            log_data['service_name'] = record.service_name
            
        # 예외 정보 추가
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)

class ElasticsearchHandler(logging.Handler):
    def __init__(self, es_client: Elasticsearch, index_name: str):
        super().__init__()
        self.es_client = es_client
        self.index_name = index_name

    def emit(self, record):
        log_entry = self.format(record)
        try:
            self.es_client.index(index=self.index_name, body=log_entry)
        except Exception:
            # Handle exceptions, e.g., log to a fallback logger
            pass
