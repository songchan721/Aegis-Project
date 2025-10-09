"""
설정 관리 시스템

Pydantic을 사용한 환경별 설정 관리
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """기본 설정 클래스"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # 애플리케이션 기본 설정
    app_name: str = Field(default="aegis-service", validation_alias="APP_NAME")
    app_version: str = Field(default="1.0.0", validation_alias="APP_VERSION")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    
    # 데이터베이스 설정
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")
    database_pool_size: int = Field(default=10, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, validation_alias="DATABASE_MAX_OVERFLOW")
    
    # Redis 설정
    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")
    redis_max_connections: int = Field(default=50, validation_alias="REDIS_MAX_CONNECTIONS")
    
    # Kafka 설정
    kafka_bootstrap_servers: Optional[str] = Field(default=None, validation_alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group_id: Optional[str] = Field(default=None, validation_alias="KAFKA_CONSUMER_GROUP_ID")
    
    # JWT 설정
    jwt_secret: Optional[str] = Field(default=None, validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")