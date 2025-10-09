"""
Aegis Shared Library

이지스(Aegis) 시스템의 모든 마이크로서비스가 공통으로 사용하는 핵심 기능을 제공하는 라이브러리
"""

from aegis_shared.version import __version__, __version_info__

__author__ = "Aegis Team"
__email__ = "team@aegis.com"

from aegis_shared.auth import AuthMiddleware, JWTHandler
from aegis_shared.cache import CacheClient

# 주요 컴포넌트 임포트
from aegis_shared.config import Settings
from aegis_shared.database import BaseRepository, DatabaseManager
from aegis_shared.logging import configure_logging, get_logger
from aegis_shared.messaging import EventPublisher
from aegis_shared.models import BaseEntity, PaginatedResponse
from aegis_shared.monitoring import MetricsCollector

__all__ = [
    "Settings",
    "configure_logging",
    "get_logger",
    "DatabaseManager",
    "BaseRepository",
    "JWTHandler",
    "AuthMiddleware",
    "CacheClient",
    "MetricsCollector",
    "EventPublisher",
    "BaseEntity",
    "PaginatedResponse",
]
