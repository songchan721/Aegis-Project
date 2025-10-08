# User Service Design Document

## Overview

User Service는 이지스(Aegis) 시스템의 사용자 인증 및 프로필 관리를 담당하는 마이크로서비스입니다.

**핵심 책임:**
1. 사용자 인증 (로그인/로그아웃)
2. JWT 토큰 발급 및 검증
3. 사용자 프로필 관리
4. 세션 관리
5. 비밀번호 재설정
6. 사용자 권한 관리 (RBAC)

**설계 원칙:**
- **보안 우선**: 모든 인증 로직은 업계 표준 준수
- **확장성**: 수평 확장 가능한 무상태(stateless) 설계
- **일관성**: shared-library를 통한 표준화된 패턴 사용
- **관찰성**: 모든 주요 작업에 대한 로깅 및 메트릭 수집

**다른 서비스와의 역할 구분:**
- **User Service**: 인증 및 사용자 기본 정보 관리
- **Policy Service**: 사용자별 정책 추천 및 관리
- **Logging-Audit Service**: 사용자 활동 감사 로그 수집

---

## Shared Library Integration

이 서비스는 `aegis-shared` 공통 라이브러리를 적극 활용합니다.

### 사용하는 모듈

```python
from aegis_shared.database import BaseRepository, DatabaseManager
from aegis_shared.auth import JWTHandler, AuthMiddleware, RBAC
from aegis_shared.messaging import VersionedEventPublisher
from aegis_shared.logging import get_logger, add_context
from aegis_shared.monitoring import track_metrics
from aegis_shared.errors import ErrorCode, AuthenticationError, EntityNotFoundError
from aegis_shared.cache import cache_result, RedisClient
from aegis_shared.config import get_config
```

### 왜 Shared Library를 사용하는가?

#### 1. JWT 처리 완전 자동화

**Before (shared-library 없이):**
```python
# ❌ 문제점: 보안 취약점, 중복 코드, 유지보수 어려움
import jwt
from datetime import datetime, timedelta

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
```

**After (shared-library 사용):**
```python
# ✅ 장점: 보안 모범 사례 자동 적용, 표준화, 유지보수 용이
from aegis_shared.auth import JWTHandler

jwt_handler = JWTHandler()

# 액세스 토큰 생성 (자동으로 만료 시간, 타입 등 설정)
access_token = jwt_handler.create_access_token(
    data={'user_id': str(user.id), 'email': user.email, 'role': user.role},
    expires_delta=timedelta(minutes=30)
)

# 리프레시 토큰 생성
refresh_token = jwt_handler.create_refresh_token(
    data={'user_id': str(user.id)},
    expires_delta=timedelta(days=7)
)

# 토큰 검증 (자동으로 만료, 서명 확인)
try:
    payload = jwt_handler.verify_token(token)
    user_id = payload['user_id']
except TokenExpiredError:
    # 표준화된 에러 처리
    pass
```

**효과:**
- 코드 라인 수 70% 감소 (50줄 → 15줄)
- 보안 취약점 제로
- 모든 서비스에서 일관된 토큰 처리

#### 2. 중앙 에러 코드 사용

**Before:**
```python
# ❌ 각 서비스마다 다른 에러 코드
raise Exception("Invalid credentials")  # 불명확
```

**After:**
```python
# ✅ 중앙 에러 코드 레지스트리 사용
from aegis_shared.errors import ErrorCode, AuthenticationError

raise AuthenticationError(
    error_code=ErrorCode.INVALID_CREDENTIALS,
    message="Invalid email or password"
)
```

**효과:**
- 프론트엔드에서 에러 코드 기반 처리 가능
- 다국어 지원 용이
- 에러 추적 및 모니터링 표준화

---

## Architecture

### 서비스 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Application]
        MOBILE[Mobile App]
    end
    
    subgraph "API Gateway"
        GATEWAY[API Gateway]
    end
    
    subgraph "User Service"
        subgraph "API Layer"
            AUTH_API[Authentication API<br/>로그인/로그아웃]
            PROFILE_API[Profile API<br/>프로필 관리]
            SESSION_API[Session API<br/>세션 관리]
        end
        
        subgraph "Business Logic"
            AUTH_SERVICE[Auth Service<br/>인증 로직]
            USER_SERVICE[User Service<br/>사용자 관리]
            TOKEN_SERVICE[Token Service<br/>JWT 관리]
        end
        
        subgraph "Data Access"
            USER_REPO[User Repository<br/>BaseRepository 상속]
            SESSION_REPO[Session Repository]
        end
    end
    
    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>사용자 데이터)]
        REDIS[(Redis<br/>세션/캐시)]
    end
    
    subgraph "Message Queue"
        KAFKA[Apache Kafka<br/>KRaft Mode]
    end
    
    subgraph "Other Services"
        POLICY_SVC[Policy Service]
        REC_SVC[Recommendation Service]
        AUDIT_SVC[Logging-Audit Service]
    end
    
    WEB --> GATEWAY
    MOBILE --> GATEWAY
    GATEWAY --> AUTH_API
    GATEWAY --> PROFILE_API
    GATEWAY --> SESSION_API
    
    AUTH_API --> AUTH_SERVICE
    PROFILE_API --> USER_SERVICE
    SESSION_API --> USER_SERVICE
    
    AUTH_SERVICE --> TOKEN_SERVICE
    AUTH_SERVICE --> USER_REPO
    USER_SERVICE --> USER_REPO
    USER_SERVICE --> SESSION_REPO
    
    USER_REPO --> POSTGRES
    SESSION_REPO --> REDIS
    
    USER_SERVICE -->|user.created<br/>user.updated<br/>user.deleted| KAFKA
    KAFKA --> POLICY_SVC
    KAFKA --> REC_SVC
    KAFKA --> AUDIT_SVC
```

### 데이터 흐름 시퀀스

```mermaid
sequenceDiagram
    participant Client
    participant API Gateway
    participant User Service
    participant PostgreSQL
    participant Redis
    participant Kafka
    
    Client->>API Gateway: POST /auth/login
    API Gateway->>User Service: 로그인 요청
    User Service->>PostgreSQL: 사용자 조회
    PostgreSQL-->>User Service: 사용자 정보
    User Service->>User Service: 비밀번호 검증
    User Service->>User Service: JWT 토큰 생성
    User Service->>Redis: 세션 저장
    User Service->>Kafka: user.logged_in 이벤트 발행
    User Service-->>API Gateway: 토큰 반환
    API Gateway-->>Client: 로그인 성공
```

---

## Components and Interfaces

### 1. Authentication API

```python
from fastapi import APIRouter, Depends, HTTPException, status
from aegis_shared.auth import JWTHandler
from aegis_shared.errors import ErrorCode, AuthenticationError
from aegis_shared.logging import get_logger
from aegis_shared.monitoring import track_metrics

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = get_logger(__name__)

@router.post("/login", response_model=TokenResponse)
@track_metrics("user_login")
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """사용자 로그인"""
    try:
        user = await auth_service.authenticate(request.email, request.password)
        tokens = await auth_service.create_tokens(user)
        
        logger.info("user_login_success", user_id=str(user.id), email=request.email)
        
        return TokenResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_type="bearer"
        )
    except AuthenticationError as e:
        logger.warning("user_login_failed", email=request.email, reason=e.error_code)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.to_dict()
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """토큰 갱신"""
    tokens = await auth_service.refresh_tokens(request.refresh_token)
    return TokenResponse(**tokens, token_type="bearer")

@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """로그아웃"""
    await auth_service.logout(current_user['user_id'])
    logger.info("user_logout", user_id=current_user['user_id'])
    return {"message": "Successfully logged out"}
```

### 2. Business Logic

```python
from aegis_shared.database import BaseRepository
from aegis_shared.auth import JWTHandler
from aegis_shared.messaging import VersionedEventPublisher
from aegis_shared.logging import get_logger
from aegis_shared.errors import ErrorCode, AuthenticationError
from aegis_shared.cache import RedisClient
import bcrypt

logger = get_logger(__name__)

class UserRepository(BaseRepository[User]):
    """사용자 Repository - BaseRepository 상속"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: UUID) -> None:
        """마지막 로그인 시간 업데이트"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.session.commit()

class AuthService:
    """인증 서비스"""
    
    def __init__(
        self,
        user_repo: UserRepository,
        jwt_handler: JWTHandler,
        redis_client: RedisClient,
        event_publisher: VersionedEventPublisher
    ):
        self.user_repo = user_repo
        self.jwt_handler = jwt_handler
        self.redis_client = redis_client
        self.event_publisher = event_publisher
    
    async def authenticate(self, email: str, password: str) -> User:
        """사용자 인증"""
        user = await self.user_repo.find_by_email(email)
        
        if not user:
            raise AuthenticationError(
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid email or password"
            )
        
        if not user.is_active:
            raise AuthenticationError(
                error_code=ErrorCode.ACCOUNT_DISABLED,
                message="Account is disabled"
            )
        
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise AuthenticationError(
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid email or password"
            )
        
        # 마지막 로그인 시간 업데이트
        await self.user_repo.update_last_login(user.id)
        
        # 로그인 이벤트 발행
        await self.event_publisher.publish(
            topic="user-events",
            event_type="user.logged_in",
            data={
                "user_id": str(user.id),
                "email": user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info("user_authenticated", user_id=str(user.id), email=email)
        return user
    
    async def create_tokens(self, user: User) -> Dict[str, str]:
        """JWT 토큰 생성"""
        access_token = self.jwt_handler.create_access_token(
            data={"user_id": str(user.id), "email": user.email, "role": user.role}
        )
        
        refresh_token = self.jwt_handler.create_refresh_token(
            data={"user_id": str(user.id)}
        )
        
        # Redis에 세션 저장
        await self.redis_client.setex(
            f"session:{user.id}",
            3600,  # 1 hour
            access_token
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
```

---

## Data Models

### API 요청/응답 모델 (Pydantic)

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class LoginRequest(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str = Field(..., min_length=8)

class RegisterRequest(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """비밀번호 강도 검증"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*()_+-=' for c in v):
            raise ValueError('Password must contain special character')
        return v

class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: UUID
    email: EmailStr
    name: str
    phone: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        orm_mode = True
```

### 데이터베이스 모델 (SQLAlchemy)

```python
from sqlalchemy import Column, String, DateTime, Enum, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PyEnum

class UserRole(str, PyEnum):
    """사용자 역할"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    # 기본 정보
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    
    # 사업자 정보
    business_type = Column(String(50))
    business_number = Column(String(50))
    industry = Column(String(100))
    region = Column(String(100))
    
    # 권한 및 상태
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # 시스템 필드
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)
    
    # 인덱스
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
        Index('idx_user_created_at', 'created_at'),
    )

class LoginHistory(Base):
    """로그인 히스토리"""
    __tablename__ = "login_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_login_history_user_id', 'user_id'),
        Index('idx_login_history_created_at', 'created_at'),
    )
```

### 이벤트 스키마 (VersionedEvent)

```python
from aegis_shared.messaging import VersionedEvent
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class UserCreatedEvent(VersionedEvent):
    """사용자 생성 이벤트"""
    event_type: str = "user.created"
    version: str = "1.0.0"
    
    class Data(BaseModel):
        user_id: UUID
        email: str
        name: str
        role: str
        created_at: datetime

class UserUpdatedEvent(VersionedEvent):
    """사용자 정보 업데이트 이벤트"""
    event_type: str = "user.updated"
    version: str = "1.0.0"
    
    class Data(BaseModel):
        user_id: UUID
        email: str
        name: str
        updated_fields: list[str]
        updated_at: datetime

class UserDeletedEvent(VersionedEvent):
    """사용자 삭제 이벤트"""
    event_type: str = "user.deleted"
    version: str = "1.0.0"
    
    class Data(BaseModel):
        user_id: UUID
        email: str
        deleted_at: datetime
```

---

## Error Handling

### 중앙 에러 코드 사용

```python
from aegis_shared.errors import ErrorCode, ServiceException

# User Service 전용 에러 코드 (중앙 레지스트리에 등록됨)
class UserErrorCode(ErrorCode):
    # 인증 관련 (1000-1099)
    INVALID_CREDENTIALS = "USER_1001"
    ACCOUNT_DISABLED = "USER_1002"
    ACCOUNT_LOCKED = "USER_1003"
    EMAIL_NOT_VERIFIED = "USER_1004"
    TOKEN_EXPIRED = "USER_1005"
    TOKEN_INVALID = "USER_1006"
    
    # 사용자 관리 (1100-1199)
    USER_NOT_FOUND = "USER_1101"
    EMAIL_ALREADY_EXISTS = "USER_1102"
    WEAK_PASSWORD = "USER_1103"
    INVALID_EMAIL_FORMAT = "USER_1104"
    
    # 세션 관리 (1200-1299)
    SESSION_NOT_FOUND = "USER_1201"
    SESSION_EXPIRED = "USER_1202"
    TOO_MANY_SESSIONS = "USER_1203"
```

### 에러 처리 전략

```python
from aegis_shared.errors import ServiceException
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class AuthenticationError(ServiceException):
    """인증 에러"""
    def __init__(self, error_code: str, message: str, details: dict = None):
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            status_code=401
        )
        logger.error("authentication_error", error_code=error_code, message=message)

class UserNotFoundError(ServiceException):
    """사용자 없음 에러"""
    def __init__(self, user_id: str):
        super().__init__(
            error_code=UserErrorCode.USER_NOT_FOUND,
            message=f"User not found: {user_id}",
            status_code=404
        )

# 글로벌 에러 핸들러
@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException):
    """서비스 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### 에러 복구 전략

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from aegis_shared.errors import ServiceException

class UserService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def create_user_with_retry(self, user_data: dict) -> User:
        """재시도 로직이 있는 사용자 생성"""
        try:
            return await self.user_repo.create(user_data)
        except DatabaseError as e:
            logger.warning("database_error_retry", attempt=e.attempt_number)
            raise
```

---

## Production Considerations

### 1. Scalability (확장성)

#### Kubernetes HPA 설정

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: user-service-hpa
  namespace: aegis
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 30
      selectPolicy: Max
```

#### 데이터베이스 연결 풀 관리

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 연결 풀 설정
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,  # 기본 연결 수
    max_overflow=10,  # 추가 연결 수
    pool_timeout=30,  # 대기 시간 (초)
    pool_recycle=3600,  # 연결 재사용 시간 (1시간)
    pool_pre_ping=True,  # 연결 유효성 사전 확인
    echo=False
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

#### 부하 분산 전략

```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: aegis
spec:
  type: ClusterIP
  sessionAffinity: None  # 무상태 설계로 세션 어피니티 불필요
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
  selector:
    app: user-service
```

### 2. Fault Tolerance (장애 복구)

#### Circuit Breaker 패턴

```python
from circuitbreaker import circuit
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class ExternalServiceClient:
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def call_external_service(self, data: dict):
        """외부 서비스 호출 (Circuit Breaker 적용)"""
        try:
            response = await self.http_client.post("/api/endpoint", json=data)
            return response.json()
        except Exception as e:
            logger.error("external_service_call_failed", error=str(e))
            raise
```

#### Retry 전략 (Tenacity)

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class UserService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseError),
        reraise=True
    )
    async def create_user_with_retry(self, user_data: dict) -> User:
        """재시도 로직이 있는 사용자 생성"""
        return await self.user_repo.create(user_data)
```

#### Timeout 설정

```python
import asyncio
from fastapi import HTTPException

async def with_timeout(coro, timeout: float = 5.0):
    """타임아웃이 있는 비동기 작업"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout")

@router.post("/users")
async def create_user(request: CreateUserRequest):
    """타임아웃이 적용된 사용자 생성"""
    return await with_timeout(
        user_service.create_user(request),
        timeout=10.0
    )
```

#### Health Check 엔드포인트

```python
from fastapi import APIRouter, status
from aegis_shared.database import DatabaseManager
from aegis_shared.cache import RedisClient

health_router = APIRouter(prefix="/health", tags=["health"])

@health_router.get("/liveness")
async def liveness():
    """Liveness Probe - 서비스 실행 여부"""
    return {"status": "alive"}

@health_router.get("/readiness")
async def readiness(
    db: DatabaseManager = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """Readiness Probe - 서비스 준비 여부"""
    checks = {
        "database": False,
        "redis": False
    }
    
    # 데이터베이스 연결 확인
    try:
        await db.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
    
    # Redis 연결 확인
    try:
        await redis.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks}
        )
```

#### Graceful Shutdown

```python
import signal
import asyncio

class Application:
    def __init__(self):
        self.is_shutting_down = False
    
    async def shutdown(self):
        """Graceful Shutdown"""
        logger.info("shutdown_initiated")
        self.is_shutting_down = True
        
        # 새로운 요청 거부
        # 진행 중인 요청 완료 대기 (최대 30초)
        await asyncio.sleep(30)
        
        # 데이터베이스 연결 종료
        await engine.dispose()
        
        # Redis 연결 종료
        await redis_client.close()
        
        logger.info("shutdown_completed")
    
    def setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.shutdown()))
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.shutdown()))
```

### 3. Caching Strategy (캐싱 전략)

#### 다층 캐싱 (L1: 메모리, L2: Redis)

```python
from functools import lru_cache
from aegis_shared.cache import cache_result, RedisClient

class UserService:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
    
    @lru_cache(maxsize=1000)  # L1: 메모리 캐시
    @cache_result(ttl=300, key_prefix="user")  # L2: Redis 캐시
    async def get_user_by_id(self, user_id: str) -> User:
        """사용자 조회 (2단계 캐싱)"""
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return user
```

#### 캐시 무효화 전략

```python
class UserService:
    async def update_user(self, user_id: str, data: dict) -> User:
        """사용자 업데이트 (캐시 무효화)"""
        # 데이터베이스 업데이트
        user = await self.user_repo.update(user_id, data)
        
        # 캐시 무효화
        await self.redis_client.delete(f"user:{user_id}")
        
        # 관련 캐시도 무효화
        await self.redis_client.delete(f"user_profile:{user_id}")
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="user-events",
            event_type="user.updated",
            data={"user_id": str(user_id), "updated_fields": list(data.keys())}
        )
        
        return user
```

#### 캐시 히트율 모니터링

```python
from prometheus_client import Counter, Histogram

cache_hits = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])

async def get_user_with_metrics(user_id: str) -> User:
    """캐시 히트율 메트릭이 있는 사용자 조회"""
    # Redis 캐시 확인
    cached = await redis_client.get(f"user:{user_id}")
    if cached:
        cache_hits.labels(cache_type='redis').inc()
        return User.parse_raw(cached)
    
    cache_misses.labels(cache_type='redis').inc()
    
    # 데이터베이스 조회
    user = await user_repo.find_by_id(user_id)
    
    # 캐시 저장
    await redis_client.setex(
        f"user:{user_id}",
        300,  # 5분 TTL
        user.json()
    )
    
    return user
```

### 4. Monitoring (모니터링)

#### Prometheus 메트릭 상세

```python
from prometheus_client import Counter, Histogram, Gauge, Info

# 비즈니스 메트릭
login_attempts_total = Counter(
    'user_login_attempts_total',
    'Total login attempts',
    ['status']  # 'success', 'failed', 'rate_limited'
)

signup_total = Counter(
    'user_signup_total',
    'Total user signups',
    ['status']  # 'success', 'failed'
)

email_verification_total = Counter(
    'user_email_verification_total',
    'Total email verifications',
    ['status']  # 'success', 'failed', 'expired'
)

password_reset_total = Counter(
    'user_password_reset_total',
    'Total password resets',
    ['status']
)

# 성능 메트릭
login_duration = Histogram(
    'user_login_duration_seconds',
    'Login duration in seconds',
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

token_verification_duration = Histogram(
    'user_token_verification_duration_seconds',
    'Token verification duration in seconds',
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5]
)

# 보안 메트릭
failed_login_attempts = Counter(
    'user_failed_login_attempts_total',
    'Failed login attempts',
    ['reason']  # 'invalid_password', 'user_not_found', 'account_locked'
)

account_lockouts = Counter(
    'user_account_lockouts_total',
    'Total account lockouts'
)

suspicious_activity = Counter(
    'user_suspicious_activity_total',
    'Suspicious activity detected',
    ['activity_type']
)

# 시스템 메트릭
active_sessions = Gauge(
    'user_active_sessions',
    'Number of active user sessions'
)

database_connections = Gauge(
    'user_database_connections',
    'Number of active database connections'
)

# 서비스 정보
service_info = Info('user_service', 'User service information')
service_info.info({
    'version': '1.0.0',
    'environment': 'production'
})
```

#### Grafana 대시보드 설정

```json
{
  "dashboard": {
    "title": "User Service Dashboard",
    "panels": [
      {
        "title": "Login Success Rate",
        "targets": [
          {
            "expr": "rate(user_login_attempts_total{status='success'}[5m]) / rate(user_login_attempts_total[5m]) * 100"
          }
        ]
      },
      {
        "title": "Login Duration (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(user_login_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "targets": [
          {
            "expr": "user_active_sessions"
          }
        ]
      },
      {
        "title": "Failed Login Attempts by Reason",
        "targets": [
          {
            "expr": "rate(user_failed_login_attempts_total[5m])"
          }
        ]
      }
    ]
  }
}
```

#### 알림 조건 및 액션

```yaml
# Prometheus Alertmanager 규칙
groups:
- name: user_service_alerts
  interval: 30s
  rules:
  # 높은 에러율
  - alert: HighLoginFailureRate
    expr: |
      rate(user_login_attempts_total{status="failed"}[5m]) 
      / rate(user_login_attempts_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
      service: user-service
    annotations:
      summary: "High login failure rate detected"
      description: "Login failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
  
  # 느린 응답 시간
  - alert: SlowLoginResponse
    expr: |
      histogram_quantile(0.95, 
        rate(user_login_duration_seconds_bucket[5m])
      ) > 2.0
    for: 5m
    labels:
      severity: warning
      service: user-service
    annotations:
      summary: "Slow login response time"
      description: "95th percentile login time is {{ $value }}s (threshold: 2s)"
  
  # 서비스 다운
  - alert: UserServiceDown
    expr: up{job="user-service"} == 0
    for: 1m
    labels:
      severity: critical
      service: user-service
    annotations:
      summary: "User service is down"
      description: "User service has been down for more than 1 minute"
  
  # 계정 잠금 급증
  - alert: HighAccountLockoutRate
    expr: rate(user_account_lockouts_total[5m]) > 10
    for: 5m
    labels:
      severity: critical
      service: user-service
    annotations:
      summary: "High account lockout rate"
      description: "Account lockout rate is {{ $value }} per second"
```

#### SLI/SLO 정의

```yaml
# Service Level Indicators (SLI)
sli:
  availability:
    metric: up{job="user-service"}
    target: 99.9%
  
  latency:
    metric: histogram_quantile(0.95, rate(user_login_duration_seconds_bucket[5m]))
    target: < 500ms
  
  error_rate:
    metric: rate(user_login_attempts_total{status="failed"}[5m]) / rate(user_login_attempts_total[5m])
    target: < 1%

# Service Level Objectives (SLO)
slo:
  - name: "Login Availability"
    description: "Login endpoint should be available 99.9% of the time"
    target: 99.9%
    window: 30d
  
  - name: "Login Latency"
    description: "95% of login requests should complete within 500ms"
    target: 95%
    threshold: 500ms
    window: 30d
  
  - name: "Login Success Rate"
    description: "99% of valid login attempts should succeed"
    target: 99%
    window: 30d
```

### 5. Security (보안)

#### 인증/인가 방법 (JWT, RBAC)

```python
from aegis_shared.auth import require_role, get_current_user, JWTHandler

# JWT 설정
jwt_handler = JWTHandler(
    secret_key=SECRET_KEY,
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)

# RBAC 적용
@router.post("/admin/users")
@require_role("admin")  # 관리자만 접근 가능
async def create_user_admin(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """관리자 전용 사용자 생성"""
    return await user_service.create_user(request)

@router.get("/users/me")
@require_role("user")  # 일반 사용자도 접근 가능
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """현재 사용자 프로필 조회"""
    return await user_service.get_user(current_user['user_id'])
```

#### 데이터 암호화

```python
import bcrypt
from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self):
        self.fernet = Fernet(ENCRYPTION_KEY)
    
    def hash_password(self, password: str) -> str:
        """비밀번호 해싱 (bcrypt)"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """민감 데이터 암호화 (Fernet)"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted: str) -> str:
        """민감 데이터 복호화"""
        return self.fernet.decrypt(encrypted.encode()).decode()
```

#### API Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/auth/login")
@limiter.limit("5/minute")  # IP당 분당 5회 제한
async def login(request: Request, login_data: LoginRequest):
    """로그인 (Rate Limiting 적용)"""
    return await auth_service.login(login_data)

@router.post("/auth/register")
@limiter.limit("3/hour")  # IP당 시간당 3회 제한
async def register(request: Request, register_data: RegisterRequest):
    """회원가입 (Rate Limiting 적용)"""
    return await auth_service.register(register_data)
```

#### 입력 검증 및 SQL Injection 방지

```python
from pydantic import BaseModel, validator, EmailStr
from sqlalchemy import text

class CreateUserRequest(BaseModel):
    email: EmailStr  # 자동 이메일 형식 검증
    name: str
    
    @validator('name')
    def validate_name(cls, v):
        """이름 검증"""
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if not v.replace(' ', '').isalnum():
            raise ValueError('Name must contain only alphanumeric characters')
        return v

# SQL Injection 방지 - Parameterized Query 사용
async def find_user_by_email(email: str) -> User:
    """안전한 쿼리 (SQL Injection 방지)"""
    # ❌ 나쁜 예: f-string 사용
    # query = f"SELECT * FROM users WHERE email = '{email}'"
    
    # ✅ 좋은 예: Parameterized Query
    query = text("SELECT * FROM users WHERE email = :email")
    result = await session.execute(query, {"email": email})
    return result.scalar_one_or_none()
```

#### 민감 정보 마스킹

```python
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

def mask_sensitive_data(data: dict) -> dict:
    """민감 정보 마스킹"""
    sensitive_fields = ['password', 'token', 'secret', 'api_key']
    masked = data.copy()
    
    for field in sensitive_fields:
        if field in masked:
            masked[field] = '***MASKED***'
    
    return masked

# 로깅 시 자동 마스킹
logger.info("user_created", **mask_sensitive_data(user_data))
```

---

## Service Integration

### 다른 서비스와의 통합

#### 이벤트 발행 목록

| 이벤트 타입 | Kafka Topic | 스키마 버전 | 발행 시점 | 구독 서비스 |
|------------|-------------|------------|----------|------------|
| user.created | user-events | 1.0.0 | 사용자 등록 완료 시 | Policy Service, Recommendation Service, Logging-Audit |
| user.updated | user-events | 1.0.0 | 사용자 정보 수정 시 | Policy Service, Recommendation Service |
| user.deleted | user-events | 1.0.0 | 사용자 삭제 시 | Policy Service, Recommendation Service, Logging-Audit |
| user.logged_in | user-events | 1.0.0 | 로그인 성공 시 | Logging-Audit, Recommendation Service |
| user.logged_out | user-events | 1.0.0 | 로그아웃 시 | Logging-Audit |
| user.password_changed | user-events | 1.0.0 | 비밀번호 변경 시 | Logging-Audit |

#### 이벤트 발행 구현

```python
from aegis_shared.messaging import VersionedEventPublisher

class UserService:
    def __init__(self, event_publisher: VersionedEventPublisher):
        self.event_publisher = event_publisher
    
    async def create_user(self, user_data: dict) -> User:
        """사용자 생성 및 이벤트 발행"""
        # 사용자 생성
        user = await self.user_repo.create(user_data)
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="user-events",
            event_type="user.created",
            version="1.0.0",
            data={
                "user_id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "created_at": user.created_at.isoformat()
            },
            partition_key=str(user.id)  # 사용자별 순서 보장
        )
        
        logger.info("user_created_event_published", user_id=str(user.id))
        return user
```

#### 이벤트 구독 목록

User Service는 현재 다른 서비스의 이벤트를 구독하지 않습니다. (독립적 서비스)

#### API 호출 관계

| 호출 대상 서비스 | 엔드포인트 | HTTP Method | 목적 | 인증 방법 | Timeout |
|----------------|-----------|-------------|------|----------|---------|
| (없음) | - | - | User Service는 다른 서비스를 호출하지 않음 | - | - |

#### 데이터베이스 연결

| 데이터베이스 | 용도 | 연결 풀 설정 | 마이그레이션 도구 |
|------------|------|-------------|----------------|
| PostgreSQL | 사용자 데이터 저장 | pool_size=20, max_overflow=10 | Alembic |
| Redis | 세션 및 캐시 | pool_size=10, max_connections=50 | N/A |

---

## Integration Testing Strategy

### 단위 테스트

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
class TestAuthService:
    async def test_authenticate_success(self):
        """인증 성공 테스트"""
        # Arrange
        user_repo = AsyncMock()
        user_repo.find_by_email.return_value = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"Test1234!", bcrypt.gensalt()).decode(),
            is_active=True
        )
        
        auth_service = AuthService(
            user_repo=user_repo,
            jwt_handler=JWTHandler(),
            redis_client=AsyncMock(),
            event_publisher=AsyncMock()
        )
        
        # Act
        user = await auth_service.authenticate("test@example.com", "Test1234!")
        
        # Assert
        assert user.email == "test@example.com"
        user_repo.find_by_email.assert_called_once_with("test@example.com")
    
    async def test_authenticate_invalid_password(self):
        """잘못된 비밀번호 테스트"""
        # Arrange
        user_repo = AsyncMock()
        user_repo.find_by_email.return_value = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"Test1234!", bcrypt.gensalt()).decode(),
            is_active=True
        )
        
        auth_service = AuthService(
            user_repo=user_repo,
            jwt_handler=JWTHandler(),
            redis_client=AsyncMock(),
            event_publisher=AsyncMock()
        )
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate("test@example.com", "WrongPassword")
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
```

### 통합 테스트

```python
@pytest.mark.integration
class TestUserServiceIntegration:
    async def test_complete_user_lifecycle(self, test_db, test_redis):
        """사용자 생명주기 통합 테스트"""
        # 1. 사용자 생성
        user_data = {
            "email": "integration@example.com",
            "password": "Test1234!",
            "name": "Integration Test"
        }
        user = await user_service.create_user(user_data)
        assert user.id is not None
        
        # 2. 사용자 조회
        found_user = await user_service.get_user(user.id)
        assert found_user.email == user_data["email"]
        
        # 3. 사용자 업데이트
        updated_user = await user_service.update_user(
            user.id,
            {"name": "Updated Name"}
        )
        assert updated_user.name == "Updated Name"
        
        # 4. 사용자 삭제
        await user_service.delete_user(user.id)
        
        # 5. 삭제 확인
        with pytest.raises(UserNotFoundError):
            await user_service.get_user(user.id)
```

### 계약 테스트 (Pact)

```python
from pact import Consumer, Provider, Like, EachLike

# Consumer 테스트 (Frontend → User Service)
pact = Consumer('frontend').has_pact_with(Provider('user-service'))

def test_login_contract():
    """로그인 API 계약 테스트"""
    expected = {
        'access_token': Like('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'),
        'refresh_token': Like('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'),
        'token_type': 'bearer'
    }
    
    (pact
     .given('user exists with valid credentials')
     .upon_receiving('a login request')
     .with_request('POST', '/api/v1/auth/login')
     .will_respond_with(200, body=expected))
    
    with pact:
        result = requests.post(
            pact.uri + '/api/v1/auth/login',
            json={'email': 'test@example.com', 'password': 'Test1234!'}
        )
        assert result.status_code == 200
        assert 'access_token' in result.json()
```

### E2E 테스트

```python
@pytest.mark.e2e
class TestAuthenticationFlow:
    async def test_complete_auth_flow(self, test_client):
        """전체 인증 플로우 E2E 테스트"""
        # 1. 회원가입
        signup_response = await test_client.post("/api/v1/auth/register", json={
            "email": "e2e@example.com",
            "password": "Test1234!",
            "name": "E2E Test User"
        })
        assert signup_response.status_code == 201
        
        # 2. 이메일 인증 (테스트 환경에서는 자동 인증)
        verify_response = await test_client.post("/api/v1/auth/verify-email", json={
            "email": "e2e@example.com",
            "code": "123456"
        })
        assert verify_response.status_code == 200
        
        # 3. 로그인
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": "e2e@example.com",
            "password": "Test1234!"
        })
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens['access_token']
        
        # 4. 인증된 요청
        profile_response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_response.status_code == 200
        assert profile_response.json()['email'] == "e2e@example.com"
        
        # 5. 로그아웃
        logout_response = await test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert logout_response.status_code == 200
```

### 부하 테스트 (Locust)

```python
from locust import HttpUser, task, between

class UserServiceLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """테스트 시작 시 로그인"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "loadtest@example.com",
            "password": "Test1234!"
        })
        self.token = response.json()['access_token']
    
    @task(3)
    def get_profile(self):
        """프로필 조회 (가중치 3)"""
        self.client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def update_profile(self):
        """프로필 업데이트 (가중치 1)"""
        self.client.put(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"name": "Updated Name"}
        )
    
    @task(2)
    def login(self):
        """로그인 (가중치 2)"""
        self.client.post("/api/v1/auth/login", json={
            "email": "loadtest@example.com",
            "password": "Test1234!"
        })
```

---

## Performance Benchmarks

### 목표 성능 지표

| 작업 | 목표 응답 시간 (p95) | 목표 TPS | 리소스 제한 |
|------|---------------------|---------|------------|
| 로그인 | < 200ms | 500 | CPU: 500m, Memory: 512Mi |
| 토큰 검증 | < 50ms | 2000 | CPU: 200m, Memory: 256Mi |
| 프로필 조회 | < 100ms | 1000 | CPU: 300m, Memory: 384Mi |
| 프로필 업데이트 | < 300ms | 200 | CPU: 500m, Memory: 512Mi |
| 회원가입 | < 500ms | 100 | CPU: 500m, Memory: 512Mi |

### 성능 측정 방법

```python
from aegis_shared.monitoring import track_metrics
import time

@track_metrics("user_login")
async def login(request: LoginRequest):
    """성능 메트릭이 추적되는 로그인"""
    start_time = time.time()
    
    try:
        user = await auth_service.authenticate(request.email, request.password)
        tokens = await auth_service.create_tokens(user)
        
        duration = time.time() - start_time
        login_duration.observe(duration)
        login_attempts_total.labels(status='success').inc()
        
        return TokenResponse(**tokens)
    except Exception as e:
        duration = time.time() - start_time
        login_duration.observe(duration)
        login_attempts_total.labels(status='failed').inc()
        raise
```

### 부하 테스트 결과 (예상)

```
Target: 500 TPS (Login)
Duration: 5 minutes
Users: 1000 concurrent

Results:
- Total Requests: 150,000
- Success Rate: 99.8%
- Average Response Time: 120ms
- p50: 100ms
- p95: 180ms
- p99: 250ms
- Max: 500ms
- Errors: 300 (0.2%)
```

---

## Monitoring

### 메트릭 수집

```python
from prometheus_client import Counter, Histogram, Gauge

# 비즈니스 메트릭
login_attempts_total = Counter(
    'user_login_attempts_total',
    'Total login attempts',
    ['status']  # 'success', 'failed', 'rate_limited'
)

signup_total = Counter(
    'user_signup_total',
    'Total signups',
    ['status']
)

email_verification_total = Counter(
    'user_email_verification_total',
    'Total email verifications',
    ['status']
)

# 성능 메트릭
login_duration = Histogram(
    'user_login_duration_seconds',
    'Login duration',
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0]
)

# 보안 메트릭
failed_login_attempts = Counter(
    'user_failed_login_attempts_total',
    'Failed login attempts',
    ['reason']  # 'invalid_password', 'user_not_found', 'rate_limited'
)

active_sessions = Gauge(
    'user_active_sessions',
    'Number of active sessions'
)
```

---

## API Specification

### OpenAPI 3.0 스펙

```yaml
openapi: 3.0.0
info:
  title: User Service API
  version: 1.0.0
  description: 사용자 인증 및 프로필 관리 API

servers:
  - url: https://api.aegis.com/user/v1
    description: Production
  - url: https://api-staging.aegis.com/user/v1
    description: Staging

paths:
  /auth/login:
    post:
      summary: 사용자 로그인
      tags:
        - Authentication
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
              properties:
                email:
                  type: string
                  format: email
                  example: user@example.com
                password:
                  type: string
                  format: password
                  minLength: 8
                  example: Test1234!
      responses:
        '200':
          description: 로그인 성공
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenResponse'
        '401':
          description: 인증 실패
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Rate limit 초과
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /auth/register:
    post:
      summary: 사용자 등록
      tags:
        - Authentication
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RegisterRequest'
      responses:
        '201':
          description: 등록 성공
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '400':
          description: 잘못된 요청
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /users/me:
    get:
      summary: 현재 사용자 프로필 조회
      tags:
        - Users
      security:
        - BearerAuth: []
      responses:
        '200':
          description: 프로필 조회 성공
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '401':
          description: 인증 필요
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    TokenResponse:
      type: object
      properties:
        access_token:
          type: string
          example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        refresh_token:
          type: string
          example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        token_type:
          type: string
          example: bearer
    
    RegisterRequest:
      type: object
      required:
        - email
        - password
        - name
      properties:
        email:
          type: string
          format: email
        password:
          type: string
          format: password
          minLength: 8
        name:
          type: string
          minLength: 2
          maxLength: 100
    
    UserResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        name:
          type: string
        role:
          type: string
          enum: [user, admin, moderator]
        is_active:
          type: boolean
        created_at:
          type: string
          format: date-time
    
    ErrorResponse:
      type: object
      properties:
        error_code:
          type: string
          example: USER_1001
        message:
          type: string
          example: Invalid credentials
        details:
          type: object
        timestamp:
          type: string
          format: date-time

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

### API 버전 관리

- **URL 버전**: `/api/v1/`, `/api/v2/`
- **하위 호환성**: 최소 6개월 유지
- **Deprecation 정책**: 3개월 전 공지

---

## Database Schema

### 스키마 정의

```sql
-- users 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    
    -- 사업자 정보
    business_type VARCHAR(50),
    business_number VARCHAR(50),
    industry VARCHAR(100),
    region VARCHAR(100),
    
    -- 권한 및 상태
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 시스템 필드
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    
    CONSTRAINT chk_role CHECK (role IN ('user', 'admin', 'moderator'))
);

-- 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = TRUE;

-- login_history 테이블
CREATE TABLE login_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 인덱스
CREATE INDEX idx_login_history_user_id ON login_history(user_id);
CREATE INDEX idx_login_history_created_at ON login_history(created_at);
CREATE INDEX idx_login_history_success ON login_history(success) WHERE success = FALSE;
```

### 참조 무결성

- **users → login_history**: ON DELETE CASCADE
- 순환 참조 없음

### 마이그레이션 (Alembic)

```python
"""create users table

Revision ID: 001
Revises: 
Create Date: 2025-10-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # users 테이블 생성
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('business_type', sa.String(50)),
        sa.Column('business_number', sa.String(50)),
        sa.Column('industry', sa.String(100)),
        sa.Column('region', sa.String(100)),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login_at', sa.DateTime())
    )
    
    # 인덱스 생성
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])

def downgrade():
    op.drop_index('idx_users_created_at')
    op.drop_index('idx_users_role')
    op.drop_index('idx_users_email')
    op.drop_table('users')
```

---

## Configuration Management

### 환경 변수

```python
from pydantic import BaseSettings, PostgresDsn, RedisDsn

class Settings(BaseSettings):
    """환경 설정"""
    # 애플리케이션
    APP_NAME: str = "user-service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    
    # 데이터베이스
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: RedisDsn
    REDIS_POOL_SIZE: int = 10
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_USER_EVENTS: str = "user-events"
    
    # 보안
    BCRYPT_ROUNDS: int = 12
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 15
    
    # 이메일
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    
    # 모니터링
    PROMETHEUS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 환경별 설정
settings = Settings()
```

### 시크릿 관리 (Kubernetes Secret)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: user-service-secrets
  namespace: aegis
type: Opaque
stringData:
  DATABASE_URL: postgresql://user:password@postgres:5432/aegis
  REDIS_URL: redis://:password@redis:6379/0
  JWT_SECRET_KEY: your-secret-key-here
  SMTP_PASSWORD: smtp-password-here
```

### Feature Flags

```python
from aegis_shared.config import FeatureFlags

class UserServiceFeatureFlags(FeatureFlags):
    """기능 토글"""
    ENABLE_EMAIL_VERIFICATION: bool = True
    ENABLE_TWO_FACTOR_AUTH: bool = False
    ENABLE_SOCIAL_LOGIN: bool = False
    ENABLE_PASSWORD_HISTORY: bool = True
    MAX_SESSIONS_PER_USER: int = 5

feature_flags = UserServiceFeatureFlags()

# 사용 예시
if feature_flags.ENABLE_EMAIL_VERIFICATION:
    await send_verification_email(user)
```

---

## Logging Strategy

### 로그 레벨 정책

```python
from aegis_shared.logging import get_logger
import logging

# 환경별 로그 레벨
LOG_LEVELS = {
    'development': logging.DEBUG,
    'staging': logging.INFO,
    'production': logging.WARNING
}

logger = get_logger(__name__, level=LOG_LEVELS[ENVIRONMENT])

# DEBUG: 개발 환경에서만
logger.debug("user_query_executed", query=query, params=params)

# INFO: 주요 이벤트
logger.info("user_created", user_id=str(user.id), email=user.email)

# WARNING: 잠재적 문제
logger.warning("login_attempt_failed", email=email, reason="invalid_password")

# ERROR: 에러 발생
logger.error("database_connection_failed", error=str(e))
```

### 로그 컨텍스트 (자동 추가)

```python
from aegis_shared.logging import add_context
from contextvars import ContextVar

# 컨텍스트 변수
request_id_var: ContextVar[str] = ContextVar('request_id', default=None)
user_id_var: ContextVar[str] = ContextVar('user_id', default=None)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """로깅 미들웨어 - 자동 컨텍스트 추가"""
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    # 인증된 사용자 ID 추가
    if hasattr(request.state, 'user'):
        user_id_var.set(str(request.state.user['user_id']))
    
    # 모든 로그에 자동 추가
    with add_context(request_id=request_id, user_id=user_id_var.get()):
        response = await call_next(request)
    
    return response
```

### 로그 보관 정책 (Elasticsearch ILM)

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### 민감 정보 마스킹

```python
import re

SENSITIVE_PATTERNS = {
    'password': r'password["\']?\s*:\s*["\']([^"\']+)["\']',
    'token': r'token["\']?\s*:\s*["\']([^"\']+)["\']',
    'api_key': r'api_key["\']?\s*:\s*["\']([^"\']+)["\']',
    'email': r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
}

def mask_sensitive_data(text: str) -> str:
    """민감 정보 마스킹"""
    for field, pattern in SENSITIVE_PATTERNS.items():
        if field == 'email':
            # 이메일은 부분 마스킹
            text = re.sub(pattern, r'\1***@\2', text)
        else:
            # 나머지는 완전 마스킹
            text = re.sub(pattern, f'{field}="***MASKED***"', text)
    return text

# 로깅 시 자동 마스킹
logger.info("user_data", data=mask_sensitive_data(json.dumps(user_data)))
```

---

## Observability

### 분산 추적 (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Tracer 설정
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = trace.get_tracer(__name__)

# Trace ID 전파
@router.post("/auth/login")
async def login(request: LoginRequest):
    """분산 추적이 적용된 로그인"""
    with tracer.start_as_current_span("user_login") as span:
        span.set_attribute("user.email", request.email)
        
        # 인증
        with tracer.start_as_current_span("authenticate_user"):
            user = await auth_service.authenticate(request.email, request.password)
        
        # 토큰 생성
        with tracer.start_as_current_span("create_tokens"):
            tokens = await auth_service.create_tokens(user)
        
        span.set_attribute("user.id", str(user.id))
        return TokenResponse(**tokens)
```

### 메트릭 수집

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 애플리케이션 메트릭
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# 비즈니스 메트릭
users_total = Gauge('users_total', 'Total number of users')
active_users_total = Gauge('active_users_total', 'Total number of active users')

# 메트릭 엔드포인트
@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return Response(generate_latest(), media_type="text/plain")
```

### 로그 집계 (ELK Stack)

```yaml
# Filebeat 설정
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/user-service/*.log
  json.keys_under_root: true
  json.add_error_key: true
  fields:
    service: user-service
    environment: production

output.logstash:
  hosts: ["logstash:5044"]
```

### 대시보드 (Grafana)

```json
{
  "dashboard": {
    "title": "User Service Observability",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total{service='user-service'}[5m])"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{service='user-service',status=~'5..'}[5m])"
        }]
      },
      {
        "title": "Response Time (p95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
        }]
      },
      {
        "title": "Active Users",
        "targets": [{
          "expr": "active_users_total"
        }]
      }
    ]
  }
}
```

---

## Disaster Recovery

### 백업 전략

```yaml
# PostgreSQL 백업 (CronJob)
apiVersion: batch/v1
kind: CronJob
metadata:
  name: user-db-backup
  namespace: aegis
spec:
  schedule: "0 2 * * *"  # 매일 새벽 2시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres -U user aegis | gzip > /backup/user-db-$(date +%Y%m%d).sql.gz
              # 30일 이상 된 백업 삭제
              find /backup -name "user-db-*.sql.gz" -mtime +30 -delete
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

### 복구 절차

**RTO (Recovery Time Objective)**: 1시간  
**RPO (Recovery Point Objective)**: 24시간

```bash
# 1. 백업에서 복구
kubectl exec -it postgres-0 -- bash
gunzip -c /backup/user-db-20251007.sql.gz | psql -U user aegis

# 2. 서비스 재시작
kubectl rollout restart deployment/user-service -n aegis

# 3. 헬스 체크 확인
kubectl get pods -n aegis -l app=user-service
curl https://api.aegis.com/user/v1/health/readiness

# 4. 메트릭 확인
# Grafana에서 에러율, 응답 시간 확인
```

### 장애 시나리오

**시나리오 1: 서비스 다운**
```bash
# 자동 복구: Kubernetes가 자동으로 Pod 재시작
# 수동 개입: 5분 이상 복구 안 될 경우
kubectl describe pod <pod-name> -n aegis
kubectl logs <pod-name> -n aegis
kubectl rollout restart deployment/user-service -n aegis
```

**시나리오 2: 데이터베이스 장애**
```bash
# 1. Read Replica로 자동 전환 (읽기 작업)
# 2. Primary 복구 시도
kubectl exec -it postgres-0 -- pg_ctl restart
# 3. 복구 실패 시 백업에서 복원
```

**시나리오 3: Redis 장애**
```bash
# 1. Redis 재시작
kubectl rollout restart statefulset/redis -n aegis
# 2. 세션 데이터 손실 - 사용자 재로그인 필요
# 3. 캐시 워밍업
```

---

## Compliance and Audit

### 데이터 보호 (GDPR 준수)

```python
class GDPRCompliance:
    """GDPR 준수 기능"""
    
    async def export_user_data(self, user_id: str) -> dict:
        """사용자 데이터 내보내기 (GDPR Article 20)"""
        user = await self.user_repo.find_by_id(user_id)
        login_history = await self.login_history_repo.find_by_user_id(user_id)
        
        return {
            "personal_data": {
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "created_at": user.created_at.isoformat()
            },
            "login_history": [
                {
                    "timestamp": h.created_at.isoformat(),
                    "ip_address": h.ip_address,
                    "success": h.success
                }
                for h in login_history
            ]
        }
    
    async def delete_user_data(self, user_id: str) -> None:
        """사용자 데이터 삭제 (GDPR Article 17 - Right to be forgotten)"""
        # 1. 사용자 데이터 익명화
        await self.user_repo.update(user_id, {
            "email": f"deleted_{user_id}@deleted.com",
            "name": "Deleted User",
            "phone": None,
            "is_active": False
        })
        
        # 2. 로그인 히스토리 삭제
        await self.login_history_repo.delete_by_user_id(user_id)
        
        # 3. 삭제 이벤트 발행
        await self.event_publisher.publish(
            topic="user-events",
            event_type="user.deleted",
            data={"user_id": str(user_id), "deleted_at": datetime.utcnow().isoformat()}
        )
```

### 감사 로그

```python
class AuditLogger:
    """감사 로그"""
    
    AUDIT_EVENTS = [
        'user.created',
        'user.updated',
        'user.deleted',
        'user.logged_in',
        'user.logged_out',
        'user.password_changed',
        'user.email_changed',
        'user.role_changed'
    ]
    
    async def log_audit_event(
        self,
        event_type: str,
        user_id: str,
        actor_id: str,
        details: dict
    ):
        """감사 이벤트 로깅"""
        audit_log = {
            "event_type": event_type,
            "user_id": user_id,
            "actor_id": actor_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": request.client.host
        }
        
        # Elasticsearch에 저장 (장기 보관)
        await self.elasticsearch.index(
            index="audit-logs",
            document=audit_log
        )
        
        logger.info("audit_event", **audit_log)
```

### 접근 제어 (RBAC)

```python
from aegis_shared.auth import require_role, require_permission

# 역할 기반 접근 제어
@router.delete("/users/{user_id}")
@require_role("admin")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """사용자 삭제 (관리자만)"""
    await audit_logger.log_audit_event(
        event_type="user.deleted",
        user_id=user_id,
        actor_id=current_user['user_id'],
        details={"reason": "admin_action"}
    )
    return await user_service.delete_user(user_id)

# 권한 기반 접근 제어
@router.put("/users/{user_id}/role")
@require_permission("user:update_role")
async def update_user_role(
    user_id: str,
    role: str,
    current_user: dict = Depends(get_current_user)
):
    """사용자 역할 변경 (특정 권한 필요)"""
    await audit_logger.log_audit_event(
        event_type="user.role_changed",
        user_id=user_id,
        actor_id=current_user['user_id'],
        details={"new_role": role}
    )
    return await user_service.update_role(user_id, role)
```

---

## Dependency Management

### 외부 라이브러리 (requirements.txt)

```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1

# Cache
redis==5.0.1
aioredis==2.0.1

# Messaging
aiokafka==0.8.1

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Monitoring
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2

# Shared Library
aegis-shared==1.0.0
```

### 버전 고정 전략

```bash
# 정확한 버전 고정 (프로덕션)
pip freeze > requirements.lock

# 보안 취약점 스캔
pip-audit

# 의존성 업데이트 (주기적)
pip list --outdated
```

### 서비스 의존성

| 서비스 | 버전 | 호환성 | 업데이트 전략 |
|--------|------|--------|--------------|
| PostgreSQL | 14.x | 13.x, 14.x, 15.x | Minor 버전 자동 업데이트 |
| Redis | 7.x | 6.x, 7.x | Minor 버전 자동 업데이트 |
| Kafka | 3.x | 3.x | Major 버전 수동 업데이트 |

---

## Development Workflow

### 로컬 개발 환경 (Docker Compose)

```yaml
version: '3.8'

services:
  user-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/aegis
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - postgres
      - redis
      - kafka
    volumes:
      - .:/app
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=aegis
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports:
      - "9092:9092"
    environment:
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_NODE_ID=1
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093

volumes:
  postgres_data:
```

### 로컬 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env

# 3. 데이터베이스 마이그레이션
alembic upgrade head

# 4. 서비스 실행
docker-compose up -d

# 5. 개발 서버 실행
uvicorn app.main:app --reload
```

### 디버깅 방법

```python
# VS Code launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### 코드 리뷰 가이드

**체크리스트**:
- [ ] 코드 스타일 준수 (PEP 8)
- [ ] 타입 힌트 포함
- [ ] 단위 테스트 작성
- [ ] 테스트 커버리지 80% 이상
- [ ] 에러 처리 적절
- [ ] 로깅 적절
- [ ] 보안 취약점 없음
- [ ] 성능 고려

### 브랜치 전략 (Git Flow)

```
main (프로덕션)
  ├── develop (개발)
  │   ├── feature/user-login
  │   ├── feature/user-profile
  │   └── feature/password-reset
  └── hotfix/security-patch
```

---

## Capacity Planning

### 리소스 요구사항

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: user-service
        image: user-service:1.0.0
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
```

### 확장 계획

**현재 (Phase 1)**:
- 사용자 수: 10,000
- TPS: 500
- Pod 수: 3
- 리소스: CPU 1.5 core, Memory 1.5GB

**6개월 후 (Phase 2)**:
- 사용자 수: 50,000 (5배)
- TPS: 2,500 (5배)
- Pod 수: 10 (3.3배)
- 리소스: CPU 5 core, Memory 5GB

**1년 후 (Phase 3)**:
- 사용자 수: 100,000 (10배)
- TPS: 5,000 (10배)
- Pod 수: 20 (6.7배)
- 리소스: CPU 10 core, Memory 10GB

### 비용 최적화

```yaml
# Spot Instance 활용 (개발/스테이징)
nodeSelector:
  node-type: spot

# Auto-scaling 최적화
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # 5분 대기
    policies:
    - type: Percent
      value: 50  # 50%씩 축소
      periodSeconds: 60
```

---

## Documentation

### API 문서 (Swagger UI)

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="User Service API",
    description="사용자 인증 및 프로필 관리 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="User Service API",
        version="1.0.0",
        description="사용자 인증 및 프로필 관리 API",
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### 운영 가이드

**배포 절차**:
```bash
# 1. 이미지 빌드
docker build -t user-service:1.0.0 .

# 2. 이미지 푸시
docker push registry.aegis.com/user-service:1.0.0

# 3. Kubernetes 배포
kubectl apply -f k8s/deployment.yaml

# 4. 배포 확인
kubectl rollout status deployment/user-service -n aegis
```

**롤백 절차**:
```bash
# 이전 버전으로 롤백
kubectl rollout undo deployment/user-service -n aegis

# 특정 버전으로 롤백
kubectl rollout undo deployment/user-service --to-revision=2 -n aegis
```

**트러블슈팅 가이드**:
- 로그인 실패 급증 → Rate Limiting 확인
- 느린 응답 시간 → 데이터베이스 연결 풀 확인
- 서비스 다운 → Pod 로그 확인, 헬스 체크 확인

---

## Versioning Strategy

### 서비스 버전 (SemVer)

```
1.0.0 - Initial Release
1.1.0 - 이메일 인증 기능 추가
1.2.0 - 소셜 로그인 기능 추가
2.0.0 - API 구조 변경 (Breaking Change)
```

### API 버전

```python
# URL 버전
@router.get("/api/v1/users/me")
async def get_profile_v1():
    """API v1"""
    pass

@router.get("/api/v2/users/me")
async def get_profile_v2():
    """API v2 - 추가 필드 포함"""
    pass

# 버전 지원 기간: 최소 6개월
# Deprecation 공지: 3개월 전
```

### 데이터베이스 스키마 버전

```bash
# Alembic 마이그레이션
alembic revision -m "add_user_preferences_table"
alembic upgrade head
alembic downgrade -1
```

---

## 사용 예시

### 1. 사용자 등록

```python
import httpx

async def register_user():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.aegis.com/user/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "name": "New User"
            }
        )
        return response.json()
```

### 2. 로그인

```python
async def login():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.aegis.com/user/v1/auth/login",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        )
        tokens = response.json()
        return tokens['access_token']
```

### 3. 프로필 조회

```python
async def get_profile(access_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.aegis.com/user/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return response.json()
```

---

**문서 버전**: 1.0.0  
**최종 업데이트**: 2025-10-07  
**작성자**: Kiro AI  
**검토자**: -  
**승인자**: -
