"""
User Service 설정

Aegis Shared Library의 설정 관리 기능을 사용한 설정 클래스
"""

from pydantic import Field, EmailStr
from aegis_shared.config import Settings

class UserServiceSettings(Settings):
    """User Service 설정"""
    
    # 애플리케이션 설정
    app_name: str = "user-service"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", env="APP_ENV")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # 데이터베이스 설정
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/user_db",
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
        default="user-service-group",
        env="KAFKA_CONSUMER_GROUP_ID"
    )
    
    # JWT 설정
    jwt_secret: str = Field(
        default="your-super-secret-key-here",
        env="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # 이메일 설정
    smtp_host: str = Field(default="localhost", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    from_email: EmailStr = Field(default="noreply@aegis.com", env="FROM_EMAIL")
    
    # 보안 설정
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    account_lockout_duration_minutes: int = Field(default=30, env="ACCOUNT_LOCKOUT_DURATION_MINUTES")
    
    # 이메일 인증 설정
    email_verification_expire_hours: int = Field(default=24, env="EMAIL_VERIFICATION_EXPIRE_HOURS")
    password_reset_expire_hours: int = Field(default=1, env="PASSWORD_RESET_EXPIRE_HOURS")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # 모니터링 설정
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9091, env="METRICS_PORT")
    
    # 레이트 리미팅 설정
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"