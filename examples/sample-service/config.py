"""
샘플 서비스 설정

Aegis Shared Library의 설정 관리 기능을 사용한 예시
"""

from pydantic import Field
from aegis_shared.config import Settings

class SampleServiceSettings(Settings):
    """샘플 서비스 설정"""
    
    # 애플리케이션 설정
    app_name: str = "sample-service"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", env="APP_ENV")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # 데이터베이스 설정
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/sample_db",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis 설정
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # Kafka 설정
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        env="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_consumer_group_id: str = Field(
        default="sample-service-group",
        env="KAFKA_CONSUMER_GROUP_ID"
    )
    
    # JWT 설정
    jwt_secret: str = Field(
        default="your-super-secret-key-here",
        env="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # 모니터링 설정
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"