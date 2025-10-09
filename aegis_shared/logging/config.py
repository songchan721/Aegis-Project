import logging
import sys
from typing import Any, Dict

from pythonjsonlogger.json import JsonFormatter

try:
    import structlog
except ImportError:
    # structlog 모듈 mock (테스트용)
    class StructlogMock:
        def configure(self, **kwargs):
            pass

    structlog = StructlogMock()


class CustomJsonFormatter(JsonFormatter):
    """커스텀 JSON 로그 포맷터"""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # event 필드 추가 (message와 동일)
        if "message" in log_record:
            log_record["event"] = log_record["message"]

        # level 필드 추가 (levelname을 소문자로)
        if "levelname" in log_record:
            log_record["level"] = log_record["levelname"].lower()

        # 요청 ID 추가
        if not log_record.get("request_id"):
            log_record["request_id"] = getattr(record, "request_id", "N/A")

        # 사용자 ID 추가
        if not log_record.get("user_id"):
            log_record["user_id"] = getattr(record, "user_id", "N/A")

        # 서비스 정보 추가
        log_record["service"] = "aegis-shared"
        log_record["timestamp"] = log_record.get("timestamp", record.created)


def configure_logging(
    service_name: str = "aegis-service",
    log_level: str = "INFO",
    format_type: str = "json",
) -> None:
    """로깅 설정"""
    setup_logging(log_level, format_type, service_name)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """로거 인스턴스 반환"""
    from .context import get_logger as context_get_logger

    return context_get_logger(name)


def setup_logging(
    level: str = "INFO", format_type: str = "json", service_name: str = "aegis-service"
) -> None:
    """로깅 설정"""

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)

    if format_type.lower() == "json":
        formatter = CustomJsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 서비스 정보 설정
    root_logger.info(f"Logging initialized for service: {service_name}")
