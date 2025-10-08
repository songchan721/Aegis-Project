"""
Aegis Shared Library 샘플 서비스

이 서비스는 aegis-shared 라이브러리의 모든 주요 기능을 사용하는 예시입니다.
- 데이터베이스 연결 및 Repository 패턴
- JWT 인증 및 권한 관리
- 구조화된 로깅
- 이벤트 발행/구독
- 캐싱
- 모니터링 및 메트릭
- 에러 처리
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import List, Optional

# Aegis Shared Library 임포트
from aegis_shared.config import Settings
from aegis_shared.logging import configure_logging, get_logger
from aegis_shared.database import DatabaseManager, BaseRepository
from aegis_shared.auth import JWTHandler, AuthMiddleware, get_current_user
from aegis_shared.messaging import EventPublisher
from aegis_shared.cache import CacheClient
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.errors.exceptions import EntityNotFoundError, ValidationError
from aegis_shared.models import BaseEntity, PaginatedResponse

# 로컬 모델 및 설정
from models import User, UserCreate, UserUpdate, UserResponse
from config import SampleServiceSettings

# 설정 로드
settings = SampleServiceSettings()

# 로깅 설정
configure_logging(
    service_name="sample-service",
    log_level=settings.log_level
)

logger = get_logger(__name__)

# 전역 컴포넌트
db_manager = None
jwt_handler = None
event_publisher = None
cache_client = None
metrics_collector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global db_manager, jwt_handler, event_publisher, cache_client, metrics_collector
    
    logger.info("Starting sample service", version="1.0.0")
    
    try:
        # 데이터베이스 초기화
        db_manager = DatabaseManager(
            database_url=settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow
        )
        
        # JWT 핸들러 초기화
        jwt_handler = JWTHandler(secret_key=settings.jwt_secret)
        
        # 이벤트 발행자 초기화
        event_publisher = EventPublisher(
            bootstrap_servers=settings.kafka_bootstrap_servers
        )
        
        # 캐시 클라이언트 초기화
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.redis_url)
        cache_client = CacheClient(redis_client=redis_client)
        
        # 메트릭 수집기 초기화
        metrics_collector = MetricsCollector()
        
        logger.info("All components initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize components", error=str(e))
        raise
    
    finally:
        # 정리 작업
        logger.info("Shutting down sample service")
        
        if db_manager:
            await db_manager.close()
        
        if event_publisher:
            event_publisher.close()
        
        if redis_client:
            await redis_client.close()
        
        logger.info("Shutdown complete")

# FastAPI 앱 생성
app = FastAPI(
    title="Sample Service",
    description="Aegis Shared Library 사용 예시 서비스",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 인증 미들웨어
@app.middleware("http")
async def auth_middleware(request, call_next):
    auth_middleware = AuthMiddleware(jwt_handler=jwt_handler)
    return await auth_middleware(request, call_next)

# Repository 클래스
class UserRepository(BaseRepository[User]):
    """사용자 Repository"""
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        from sqlalchemy import select
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.email == email)
        )
        return result.scalar_one_or_none()

# 의존성 함수들
async def get_db_session():
    """데이터베이스 세션 의존성"""
    async with db_manager.session() as session:
        yield session

async def get_user_repository(session=Depends(get_db_session)):
    """사용자 Repository 의존성"""
    return UserRepository(session, User)

async def get_cache():
    """캐시 클라이언트 의존성"""
    return cache_client

async def get_metrics():
    """메트릭 수집기 의존성"""
    return metrics_collector

async def get_event_publisher():
    """이벤트 발행자 의존성"""
    return event_publisher

# API 엔드포인트들

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "sample-service"}

@app.get("/metrics")
async def get_metrics_endpoint(metrics: MetricsCollector = Depends(get_metrics)):
    """Prometheus 메트릭 엔드포인트"""
    return metrics.generate_metrics()

@app.post("/auth/login")
async def login(email: str, password: str):
    """로그인 (JWT 토큰 생성 예시)"""
    # 실제로는 비밀번호 검증 로직이 필요
    if email == "admin@example.com" and password == "password":
        token = jwt_handler.create_access_token({
            "user_id": "user-123",
            "email": email,
            "role": "admin"
        })
        
        logger.info("User logged in", email=email)
        
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.post("/users/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository),
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user: dict = Depends(get_current_user)
):
    """사용자 생성"""
    logger.info("Creating user", email=user_data.email)
    
    # 중복 확인
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise ValidationError("Email already exists")
    
    # 사용자 생성
    user = User(**user_data.dict())
    created_user = await user_repo.create(user)
    
    # 이벤트 발행
    await publisher.publish(
        topic="user-events",
        event_type="user.created",
        data={
            "user_id": str(created_user.id),
            "email": created_user.email,
            "name": created_user.name
        },
        key=str(created_user.id)
    )
    
    logger.info("User created successfully", user_id=str(created_user.id))
    
    return UserResponse.from_orm(created_user)

@app.get("/users/", response_model=PaginatedResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_current_user)
):
    """사용자 목록 조회"""
    users = await user_repo.list(skip=skip, limit=limit)
    total = await user_repo.count()
    
    user_responses = [UserResponse.from_orm(user) for user in users]
    
    return PaginatedResponse.create(
        items=user_responses,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_current_user)
):
    """사용자 조회 (캐시됨)"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundError("User", user_id)
    
    return UserResponse.from_orm(user)

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
    cache: CacheClient = Depends(get_cache),
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user: dict = Depends(get_current_user)
):
    """사용자 업데이트"""
    # 사용자 존재 확인
    existing_user = await user_repo.get_by_id(user_id)
    if not existing_user:
        raise EntityNotFoundError("User", user_id)
    
    # 업데이트
    update_data = user_data.dict(exclude_unset=True)
    updated_user = await user_repo.update(user_id, **update_data)
    
    # 캐시 무효화
    await cache.delete(f"user:{user_id}")
    
    # 이벤트 발행
    await publisher.publish(
        topic="user-events",
        event_type="user.updated",
        data={
            "user_id": user_id,
            "changes": update_data
        },
        key=user_id
    )
    
    logger.info("User updated", user_id=user_id, changes=update_data)
    
    return UserResponse.from_orm(updated_user)

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user_repo: UserRepository = Depends(get_user_repository),
    cache: CacheClient = Depends(get_cache),
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user: dict = Depends(get_current_user)
):
    """사용자 삭제 (소프트 삭제)"""
    # 사용자 존재 확인
    existing_user = await user_repo.get_by_id(user_id)
    if not existing_user:
        raise EntityNotFoundError("User", user_id)
    
    # 소프트 삭제
    await user_repo.soft_delete(user_id)
    
    # 캐시 무효화
    await cache.delete(f"user:{user_id}")
    
    # 이벤트 발행
    await publisher.publish(
        topic="user-events",
        event_type="user.deleted",
        data={"user_id": user_id},
        key=user_id
    )
    
    logger.info("User deleted", user_id=user_id)
    
    return {"message": "User deleted successfully"}

@app.get("/users/{user_id}/analytics")
async def get_user_analytics(
    user_id: str,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_current_user)
):
    """사용자 분석 데이터 (메트릭 수집 예시)"""
    # 사용자 존재 확인
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundError("User", user_id)
    
    # 분석 데이터 생성 (예시)
    analytics = {
        "user_id": user_id,
        "login_count": 42,
        "last_login": "2024-01-15T10:30:00Z",
        "activity_score": 85.5
    }
    
    # 커스텀 메트릭 기록
    metrics_collector.increment_counter(
        "user_analytics_requests_total",
        labels={"user_id": user_id}
    )
    
    return analytics

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )