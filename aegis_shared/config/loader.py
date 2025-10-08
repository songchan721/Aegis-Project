import os
from typing import Dict, Any, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """기본 설정 클래스"""

    # 애플리케이션 설정
    app_name: str = Field(default="aegis-service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")

    # 서버 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    workers: int = Field(default=1, env="WORKERS")

    # 데이터베이스 설정
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")

    # Redis 설정
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")

    # Kafka 설정
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group_id: str = Field(default="aegis-consumer", env="KAFKA_CONSUMER_GROUP_ID")
    kafka_auto_offset_reset: str = Field(default="latest", env="KAFKA_AUTO_OFFSET_RESET")

    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")

    # 모니터링 설정
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    metrics_path: str = Field(default="/metrics", env="METRICS_PATH")

    # 보안 설정
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

    # API 설정
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    api_rate_limit: int = Field(default=1000, env="API_RATE_LIMIT")
    api_rate_window: int = Field(default=900, env="API_RATE_WINDOW")  # 15분

    # 외부 서비스 설정
    external_service_timeout: int = Field(default=30, env="EXTERNAL_SERVICE_TIMEOUT")
    external_service_retries: int = Field(default=3, env="EXTERNAL_SERVICE_RETRIES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator('app_env')
    @classmethod
    def validate_app_env(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('app_env must be one of: development, staging, production')
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of: {valid_levels}')
        return v.upper()

class ConfigLoader:
    """설정 로더"""

    def __init__(self):
        self._settings: Optional[Settings] = None
        self._cache: Dict[str, Any] = {}

    def load(self) -> Settings:
        """설정 로드"""
        if self._settings is None:
            self._settings = Settings()
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        settings = self.load()
        return getattr(settings, key, default)

    def get_all(self) -> Dict[str, Any]:
        """모든 설정 조회"""
        settings = self.load()
        return settings.dict()

    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.get('app_env') == 'development'

    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.get('app_env') == 'production'

    def is_staging(self) -> bool:
        """스테이징 환경 여부"""
        return self.get('app_env') == 'staging'

# 전역 설정 로더
_config_loader = ConfigLoader()

def get_config() -> Settings:
    """전역 설정 조회"""
    return _config_loader.load()

def get_config_value(key: str, default: Any = None) -> Any:
    """전역 설정값 조회"""
    return _config_loader.get(key, default)

def is_development() -> bool:
    """개발 환경 여부"""
    return _config_loader.is_development()

def is_production() -> bool:
    """프로덕션 환경 여부"""
    return _config_loader.is_production()

def is_staging() -> bool:
    """스테이징 환경 여부"""
    return _config_loader.is_staging()
