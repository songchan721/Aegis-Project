"""
설정 관리 시스템

Pydantic을 사용한 환경별 설정 관리
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """기본 설정 클래스"""
    
    # 애플리케이션 기본 설정
    app_name: str = Field(default="aegis-service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # 데이터베이스 설정
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis 설정
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # Kafka 설정
    kafka_bootstrap_servers: Optional[str] = Field(default=None, env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group_id: Optional[str] = Field(default=None, env="KAFKA_CONSUMER_GROUP_ID")
    
    # JWT 설정
    jwt_secret: Optional[str] = Field(default=None, env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False