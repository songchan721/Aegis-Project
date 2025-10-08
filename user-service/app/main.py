"""
User Service 메인 애플리케이션

Aegis Shared Library를 사용한 사용자 인증 및 관리 서비스
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import Optional

# Aegis Shared Library 임포트
from aegis_shared.config import Settings
from aegis_shared.logging import configure_logging, get_logger
from aegis_shared.database import DatabaseManager
from aegis_shared.auth import JWTHandler, AuthMiddleware
from aegis_shared.messaging import EventPublisher
from aegis_shared.cache import CacheClient
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.errors.exceptions import ServiceException

# 로컬 설정 및 컴포넌트
from app.config import UserServiceSettings

# 설정 로드
settings = UserServiceSettings()

# 로깅 설정
configure_logging(
    service_name=settings.app_name,
    log_level=settings.log_level
)

logger = get_logger(__name__)

# 전역 컴포넌트
db_manager: Optional[DatabaseManager] = None
jwt_handler: Optional[JWTHandler] = None
event_publisher: Optional[EventPublisher] = None
cache_client: Optional[CacheClient] = None
metrics_collector: Optional[MetricsCollector] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global db_manager, jwt_handler, event_publisher, cache_client, metrics_collector
    
    logger.info("Starting User Service", version=settings.app_version)
    
    try:
        # 데이터베이스 초기화
        db_manager = DatabaseManager(
            database_url=settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow
        )
        logger.info("Database manager initialized")
        
        # JWT 핸들러 초기화
        jwt_handler = JWTHandler(
            secret_key=settings.jwt_secret,
            algorithm=settings.jwt_algorithm
        )
        logger.info("JWT handler initialized")
        
        # 이벤트 발행자 초기화
        event_publisher = EventPublisher(
            bootstrap_servers=settings.kafka_bootstrap_servers
        )
        logger.info("Event publisher initialized")
        
        # 캐시 클라이언트 초기화
        import redis.asyncio as redis
        redis_client = redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections
        )
        cache_client = CacheClient(redis_client=redis_client)
        logger.info("Cache client initialized")
        
        # 메트릭 수집기 초기화
        metrics_collector = MetricsCollector()
        logger.info("Metrics collector initialized")
        
        logger.info("All components initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize components", error=str(e))
        raise
    
    finally:
        # 정리 작업
        logger.info("Shutting down User Service")
        
        if db_manager:
            await db_manager.close()
            logger.info("Database connections closed")
        
        if event_publisher:
            event_publisher.close()
            logger.info("Event publisher closed")
        
        if cache_client and hasattr(cache_client, 'redis_client'):
            await cache_client.redis_client.close()
            logger.info("Cache client closed")
        
        logger.info("Shutdown complete")

# FastAPI 앱 생성
app = FastAPI(
    title="User Service",
    description="Aegis 사용자 인증 및 관리 서비스",
    version=settings.app_version,
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 인증 미들웨어
@app.middleware("http")
async def auth_middleware(request, call_next):
    if jwt_handler:
        auth_middleware_instance = AuthMiddleware(jwt_handler=jwt_handler)
        return await auth_middleware_instance(request, call_next)
    return await call_next(request)

# 전역 예외 핸들러
@app.exception_handler(ServiceException)
async def service_exception_handler(request, exc: ServiceException):
    """서비스 예외 처리"""
    logger.error(
        "Service exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path
    )
    
    return HTTPException(
        status_code=getattr(exc, 'status_code', 500),
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": getattr(exc, 'details', {})
        }
    )

# 의존성 함수들
async def get_db_session():
    """데이터베이스 세션 의존성"""
    if not db_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    async with db_manager.session() as session:
        yield session

async def get_cache():
    """캐시 클라이언트 의존성"""
    if not cache_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not available"
        )
    return cache_client

async def get_metrics():
    """메트릭 수집기 의존성"""
    if not metrics_collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics collector not available"
        )
    return metrics_collector

async def get_event_publisher():
    """이벤트 발행자 의존성"""
    if not event_publisher:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event publisher not available"
        )
    return event_publisher

# 기본 엔드포인트들

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "user-service",
        "version": settings.app_version,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    health_status = {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "components": {
            "database": db_manager is not None,
            "cache": cache_client is not None,
            "messaging": event_publisher is not None,
            "metrics": metrics_collector is not None
        }
    }
    
    # 모든 컴포넌트가 정상인지 확인
    all_healthy = all(health_status["components"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/metrics")
async def get_metrics_endpoint(metrics: MetricsCollector = Depends(get_metrics)):
    """Prometheus 메트릭 엔드포인트"""
    return metrics.generate_metrics()

# 라우터 등록 (추후 구현될 라우터들)
# from app.routers import auth, users, sessions
# app.include_router(auth.router, prefix="/auth", tags=["authentication"])
# app.include_router(users.router, prefix="/users", tags=["users"])
# app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )