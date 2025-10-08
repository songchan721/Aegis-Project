# 시작하기 (Getting Started)

Aegis Shared Library를 사용하여 마이크로서비스를 개발하는 방법을 단계별로 안내합니다.

## 1. 설치 및 설정

### 1.1 패키지 설치

```bash
# Poetry를 사용하는 경우 (권장)
poetry add aegis-shared

# pip를 사용하는 경우
pip install aegis-shared
```

### 1.2 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다:

```bash
# 애플리케이션 설정
APP_NAME=my-service
APP_VERSION=1.0.0
APP_ENV=development

# 서버 설정
HOST=0.0.0.0
PORT=8000
DEBUG=true

# 데이터베이스 설정
DATABASE_URL=postgresql+asyncpg://user:password@localhost/mydb
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis 설정
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Kafka 설정
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP_ID=my-service-group

# JWT 설정
JWT_SECRET=your-super-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 로깅 설정
LOG_LEVEL=INFO
LOG_FORMAT=json

# 모니터링 설정
METRICS_ENABLED=true
METRICS_PORT=9090
```

### 1.3 기본 설정 로드

```python
# config.py
from aegis_shared.config import Settings

# 설정 로드
settings = Settings()

# 설정 확인
print(f"Service: {settings.app_name}")
print(f"Environment: {settings.app_env}")
print(f"Database: {settings.database_url}")
```

## 2. FastAPI 애플리케이션 설정

### 2.1 기본 애플리케이션 구조

```python
# main.py
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from aegis_shared.config import Settings
from aegis_shared.logging import configure_logging, get_logger
from aegis_shared.database import DatabaseManager
from aegis_shared.auth import JWTHandler, AuthMiddleware
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.cache import CacheClient

# 설정 로드
settings = Settings()

# 로깅 설정
configure_logging(
    service_name=settings.app_name,
    log_level=settings.log_level
)

logger = get_logger(__name__)

# 전역 컴포넌트
db_manager = None
jwt_handler = None
cache_client = None
metrics_collector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global db_manager, jwt_handler, cache_client, metrics_collector
    
    # 시작 시 초기화
    logger.info("Starting application", service=settings.app_name)
    
    # 데이터베이스 초기화
    db_manager = DatabaseManager(
        database_url=settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow
    )
    
    # JWT 핸들러 초기화
    jwt_handler = JWTHandler(secret_key=settings.jwt_secret)
    
    # 캐시 클라이언트 초기화
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.redis_url)
    cache_client = CacheClient(redis_client=redis_client)
    
    # 메트릭 수집기 초기화
    metrics_collector = MetricsCollector()
    
    logger.info("Application started successfully")
    
    yield
    
    # 종료 시 정리
    logger.info("Shutting down application")
    
    if db_manager:
        await db_manager.close()
    
    if redis_client:
        await redis_client.close()
    
    logger.info("Application shutdown complete")

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# 인증 미들웨어 추가
@app.middleware("http")
async def auth_middleware(request, call_next):
    auth_middleware = AuthMiddleware(jwt_handler=jwt_handler)
    return await auth_middleware(request, call_next)

# 의존성 함수들
async def get_db_session():
    """데이터베이스 세션 의존성"""
    async with db_manager.session() as session:
        yield session

async def get_cache():
    """캐시 클라이언트 의존성"""
    return cache_client

async def get_metrics():
    """메트릭 수집기 의존성"""
    return metrics_collector
```

### 2.2 라우터 설정

```python
# routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from aegis_shared.models import BaseEntity
from aegis_shared.database import BaseRepository
from aegis_shared.auth import get_current_user
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.logging import get_logger

from ..models import User, UserCreate, UserResponse
from ..dependencies import get_db_session, get_metrics

router = APIRouter(prefix="/users", tags=["users"])
logger = get_logger(__name__)

class UserRepository(BaseRepository[User]):
    pass

@router.post("/", response_model=UserResponse)
@metrics_collector.track_requests()
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    metrics: MetricsCollector = Depends(get_metrics),
    current_user: dict = Depends(get_current_user)
):
    """사용자 생성"""
    logger.info("Creating user", user_email=user_data.email)
    
    user_repo = UserRepository(session, User)
    
    # 중복 확인
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # 사용자 생성
    user = User(**user_data.dict())
    created_user = await user_repo.create(user)
    
    logger.info("User created successfully", user_id=created_user.id)
    
    return UserResponse.from_orm(created_user)

@router.get("/", response_model=List[UserResponse])
@metrics_collector.track_requests()
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """사용자 목록 조회"""
    user_repo = UserRepository(session, User)
    users = await user_repo.list(skip=skip, limit=limit)
    
    return [UserResponse.from_orm(user) for user in users]
```

## 3. 데이터 모델 정의

### 3.1 데이터베이스 모델

```python
# models/database.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
```

### 3.2 API 모델

```python
# models/api.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

## 4. 이벤트 처리

### 4.1 이벤트 발행

```python
# services/user_service.py
from aegis_shared.messaging import EventPublisher
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class UserService:
    def __init__(self, event_publisher: EventPublisher):
        self.event_publisher = event_publisher
    
    async def create_user(self, user_data: dict) -> User:
        """사용자 생성 및 이벤트 발행"""
        # 사용자 생성 로직
        user = await self._create_user_in_db(user_data)
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="user-events",
            event_type="user.created",
            data={
                "user_id": user.id,
                "email": user.email,
                "name": user.name
            },
            key=str(user.id)
        )
        
        logger.info("User created and event published", user_id=user.id)
        
        return user
```

### 4.2 이벤트 구독

```python
# event_handlers.py
from aegis_shared.messaging import EventSubscriber
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

# 이벤트 구독자 초기화
subscriber = EventSubscriber(
    bootstrap_servers="localhost:9092",
    group_id="my-service-group",
    topics=["user-events", "policy-events"]
)

@subscriber.handler("user.created")
async def handle_user_created(event):
    """사용자 생성 이벤트 처리"""
    user_data = event["data"]
    logger.info("Processing user created event", user_id=user_data["user_id"])
    
    # 비즈니스 로직 처리
    await send_welcome_email(user_data["email"])
    await create_user_profile(user_data)

@subscriber.handler("user.updated")
async def handle_user_updated(event):
    """사용자 업데이트 이벤트 처리"""
    user_data = event["data"]
    logger.info("Processing user updated event", user_id=user_data["user_id"])
    
    # 캐시 무효화
    await invalidate_user_cache(user_data["user_id"])

# 이벤트 구독자 시작
async def start_event_subscriber():
    await subscriber.start()
```

## 5. 캐싱 구현

### 5.1 캐시 데코레이터 사용

```python
# services/policy_service.py
from aegis_shared.cache import CacheClient
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class PolicyService:
    def __init__(self, cache_client: CacheClient):
        self.cache = cache_client
    
    @cache_client.cached(ttl=300)  # 5분 캐시
    async def get_user_policies(self, user_id: str):
        """사용자 정책 조회 (캐시됨)"""
        logger.info("Fetching user policies", user_id=user_id)
        
        # 데이터베이스에서 조회
        policies = await self._fetch_policies_from_db(user_id)
        
        return policies
    
    async def update_user_policy(self, user_id: str, policy_data: dict):
        """사용자 정책 업데이트"""
        # 정책 업데이트
        policy = await self._update_policy_in_db(user_id, policy_data)
        
        # 관련 캐시 무효화
        await self.cache.delete(f"user_policies:{user_id}")
        
        return policy
```

### 5.2 수동 캐시 관리

```python
async def get_user_with_cache(user_id: str, cache: CacheClient):
    """캐시를 사용한 사용자 조회"""
    cache_key = f"user:{user_id}"
    
    # 캐시에서 조회
    cached_user = await cache.get(cache_key)
    if cached_user:
        logger.info("User found in cache", user_id=user_id)
        return cached_user
    
    # 데이터베이스에서 조회
    user = await fetch_user_from_db(user_id)
    if user:
        # 캐시에 저장 (1시간)
        await cache.set(cache_key, user, ttl=3600)
        logger.info("User cached", user_id=user_id)
    
    return user
```

## 6. 모니터링 및 로깅

### 6.1 메트릭 수집

```python
# 메트릭 데코레이터 사용
@metrics_collector.track_requests()
@metrics_collector.track_database_queries()
async def get_user_analytics(user_id: str):
    """사용자 분석 데이터 조회"""
    # 비즈니스 로직
    return analytics_data

# 커스텀 메트릭
async def process_policy_application(application_data: dict):
    """정책 신청 처리"""
    start_time = time.time()
    
    try:
        # 처리 로직
        result = await process_application(application_data)
        
        # 성공 메트릭
        metrics_collector.increment_counter(
            "policy_applications_processed_total",
            labels={"status": "success", "policy_type": application_data["type"]}
        )
        
        return result
        
    except Exception as e:
        # 실패 메트릭
        metrics_collector.increment_counter(
            "policy_applications_processed_total",
            labels={"status": "error", "policy_type": application_data["type"]}
        )
        raise
    
    finally:
        # 처리 시간 메트릭
        processing_time = time.time() - start_time
        metrics_collector.observe_histogram(
            "policy_application_processing_duration_seconds",
            value=processing_time,
            labels={"policy_type": application_data["type"]}
        )
```

### 6.2 구조화된 로깅

```python
from aegis_shared.logging import get_logger, add_context

logger = get_logger(__name__)

async def process_user_request(request_id: str, user_id: str):
    """사용자 요청 처리"""
    # 로깅 컨텍스트 설정
    add_context(request_id=request_id, user_id=user_id)
    
    logger.info("Processing user request", action="start")
    
    try:
        # 비즈니스 로직
        result = await perform_business_logic()
        
        logger.info(
            "User request processed successfully",
            action="complete",
            result_count=len(result)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "User request processing failed",
            action="error",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise
```

## 7. 에러 처리

### 7.1 전역 에러 핸들러

```python
# main.py
from fastapi import Request
from fastapi.responses import JSONResponse
from aegis_shared.errors.exceptions import (
    ServiceException,
    ValidationError,
    EntityNotFoundError,
    AuthenticationError
)

@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException):
    """서비스 예외 처리"""
    logger.error(
        "Service exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """검증 에러 처리"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation failed",
            "details": exc.details
        }
    )
```

### 7.2 비즈니스 로직에서 에러 처리

```python
from aegis_shared.errors.exceptions import EntityNotFoundError, ValidationError

async def get_user_by_id(user_id: str):
    """사용자 조회"""
    if not user_id:
        raise ValidationError("User ID is required")
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundError("User", user_id)
    
    return user
```

## 8. 테스트

### 8.1 단위 테스트

```python
# tests/test_user_service.py
import pytest
from unittest.mock import AsyncMock, Mock

from aegis_shared.database import BaseRepository
from services.user_service import UserService

@pytest.fixture
def mock_user_repo():
    return AsyncMock(spec=BaseRepository)

@pytest.fixture
def mock_event_publisher():
    return AsyncMock()

@pytest.fixture
def user_service(mock_user_repo, mock_event_publisher):
    return UserService(
        user_repo=mock_user_repo,
        event_publisher=mock_event_publisher
    )

@pytest.mark.asyncio
async def test_create_user_success(user_service, mock_user_repo, mock_event_publisher):
    """사용자 생성 성공 테스트"""
    # Given
    user_data = {"email": "test@example.com", "name": "Test User"}
    mock_user = Mock(id=1, email="test@example.com", name="Test User")
    mock_user_repo.create.return_value = mock_user
    
    # When
    result = await user_service.create_user(user_data)
    
    # Then
    assert result == mock_user
    mock_user_repo.create.assert_called_once()
    mock_event_publisher.publish.assert_called_once()
```

### 8.2 통합 테스트

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app, get_db_session

@pytest.fixture
async def test_db():
    """테스트 데이터베이스 설정"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = sessionmaker(engine, class_=AsyncSession)
    
    yield session_factory
    
    await engine.dispose()

@pytest.fixture
def client(test_db):
    """테스트 클라이언트"""
    async def override_get_db():
        async with test_db() as session:
            yield session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client

def test_create_user_integration(client):
    """사용자 생성 통합 테스트"""
    user_data = {
        "email": "test@example.com",
        "name": "Test User"
    }
    
    response = client.post("/users/", json=user_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert "id" in data
```

## 9. 배포

### 9.1 Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Poetry 설치
RUN pip install poetry

# 의존성 파일 복사
COPY pyproject.toml poetry.lock ./

# 의존성 설치
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@db:5432/mydb
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - db
      - redis
      - kafka

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    depends_on:
      - zookeeper

volumes:
  postgres_data:
```

## 10. 모범 사례

### 10.1 코드 구조

```
my-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱
│   ├── config.py            # 설정
│   ├── dependencies.py      # 의존성
│   ├── models/              # 데이터 모델
│   │   ├── __init__.py
│   │   ├── database.py      # DB 모델
│   │   └── api.py           # API 모델
│   ├── routers/             # API 라우터
│   │   ├── __init__.py
│   │   └── users.py
│   ├── services/            # 비즈니스 로직
│   │   ├── __init__.py
│   │   └── user_service.py
│   └── repositories/        # 데이터 접근
│       ├── __init__.py
│       └── user_repository.py
├── tests/                   # 테스트
├── alembic/                 # 마이그레이션
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

### 10.2 개발 팁

1. **환경 분리**: 개발, 스테이징, 프로덕션 환경 분리
2. **로깅**: 모든 중요한 작업에 로깅 추가
3. **메트릭**: 비즈니스 메트릭과 기술 메트릭 모두 수집
4. **에러 처리**: 명확하고 일관된 에러 처리
5. **테스트**: 단위 테스트와 통합 테스트 작성
6. **문서화**: API 문서와 코드 주석 작성
7. **보안**: 인증, 인가, 입력 검증 철저히
8. **성능**: 캐싱, 페이지네이션, 인덱스 활용

이제 Aegis Shared Library를 사용하여 견고하고 확장 가능한 마이크로서비스를 개발할 수 있습니다!