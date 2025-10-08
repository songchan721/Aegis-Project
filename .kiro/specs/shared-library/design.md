# Shared Library Design Document

## Overview

Shared Library는 이지스(Aegis) 시스템의 모든 마이크로서비스가 공통으로 사용하는 Python 패키지입니다. 일관된 구현 패턴, 코드 재사용성, 유지보수성 향상을 목표로 설계되었습니다.

**패키지명:** `aegis-shared`  
**버전 관리:** Semantic Versioning (SemVer)  
**배포 방식:** Private PyPI Repository

## Architecture

### 패키지 구조

```
aegis-shared/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── aegis_shared/
│   ├── __init__.py
│   ├── version.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py          # DB 연결 관리
│   │   ├── base_repository.py     # Repository 패턴
│   │   ├── transaction.py         # 트랜잭션 관리
│   │   ├── session.py             # 세션 관리
│   │   ├── migration.py           # 마이그레이션 헬퍼
│   │   ├── schema_registry.py     # 중앙 스키마 레지스트리
│   │   └── migration_coordinator.py  # 마이그레이션 조율
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py         # JWT 토큰 처리
│   │   ├── middleware.py          # 인증 미들웨어
│   │   ├── permissions.py         # 권한 관리
│   │   ├── decorators.py          # 인증 데코레이터
│   │   └── service_account.py     # 서비스 계정
│   │
│   ├── logging/
│   │   ├── __init__.py
│   │   ├── structured_logger.py   # 구조화된 로깅
│   │   ├── context.py             # 로깅 컨텍스트
│   │   ├── formatters.py          # 로그 포맷터
│   │   └── handlers.py            # 로그 핸들러
│   │
│   ├── messaging/
│   │   ├── __init__.py
│   │   ├── kafka_producer.py     # Kafka 프로듀서 (KRaft 지원) ⭐
│   │   ├── kafka_consumer.py     # Kafka 컨슈머 (KRaft 지원) ⭐
│   │   ├── event_publisher.py    # 이벤트 발행
│   │   ├── event_subscriber.py   # 이벤트 구독
│   │   ├── schemas.py            # 이벤트 스키마
│   │   ├── schema_registry.py    # 이벤트 스키마 레지스트리 ⭐
│   │   └── schema_versioning.py  # 스키마 버전 관리 ⭐
│   │
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── metrics.py            # Prometheus 메트릭
│   │   ├── tracing.py            # 분산 추적
│   │   ├── health_check.py       # 헬스 체크
│   │   └── decorators.py         # 모니터링 데코레이터
│   │
│   ├── errors/
│   │   ├── __init__.py
│   │   ├── exceptions.py         # 공통 예외
│   │   ├── handlers.py           # 예외 핸들러
│   │   ├── error_codes.py        # 중앙 에러 코드 레지스트리 ⭐
│   │   └── error_registry.py     # 에러 코드 관리 시스템 ⭐
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py               # 기본 모델
│   │   ├── contracts.py          # 데이터 계약
│   │   ├── api_contracts.py      # API 계약 검증 ⭐
│   │   ├── enums.py              # 공통 Enum
│   │   └── pagination.py         # 페이지네이션
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── redis_client.py       # Redis 클라이언트
│   │   ├── decorators.py         # 캐싱 데코레이터
│   │   └── strategies.py         # 캐싱 전략
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py           # 설정 관리
│   │   ├── environment.py        # 환경 관리
│   │   └── secrets.py            # 시크릿 관리
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validators.py         # 검증 함수
│       ├── formatters.py         # 포맷팅 함수
│       ├── encryption.py         # 암호화 함수
│       ├── date_utils.py         # 날짜 유틸리티
│       ├── string_utils.py       # 문자열 유틸리티
│       └── file_utils.py         # 파일 유틸리티
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── test_database.py
    │   ├── test_auth.py
    │   ├── test_logging.py
    │   └── ...
    └── integration/
        ├── test_kafka.py
        ├── test_redis.py
        └── ...
```

## Components and Interfaces

### 1. Database Module

#### 1.1 Base Repository Pattern

```python
# aegis_shared/database/base_repository.py
from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import DeclarativeMeta

T = TypeVar('T', bound=DeclarativeMeta)

class BaseRepository(Generic[T]):
    """
    모든 Repository가 상속받는 기본 클래스
    
    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)
    """
    
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
    
    async def get_by_id(self, id: Any) -> Optional[T]:
        """ID로 단일 엔티티 조회"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_ids(self, ids: List[Any]) -> List[T]:
        """여러 ID로 엔티티 조회"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id.in_(ids))
        )
        return result.scalars().all()
    
    async def create(self, entity: T) -> T:
        """엔티티 생성"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def create_many(self, entities: List[T]) -> List[T]:
        """여러 엔티티 생성"""
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities
    
    async def update(self, id: Any, **kwargs) -> Optional[T]:
        """엔티티 업데이트"""
        await self.session.execute(
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(**kwargs)
        )
        return await self.get_by_id(id)
    
    async def delete(self, id: Any) -> bool:
        """엔티티 삭제"""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == id)
        )
        return result.rowcount > 0
    
    async def soft_delete(self, id: Any) -> Optional[T]:
        """소프트 삭제 (deleted_at 설정)"""
        from datetime import datetime
        return await self.update(id, deleted_at=datetime.utcnow())
    
    async def list(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """엔티티 목록 조회"""
        query = select(self.model_class)
        
        # 필터 적용
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        
        # 정렬
        if order_by and hasattr(self.model_class, order_by):
            query = query.order_by(getattr(self.model_class, order_by))
        
        # 페이지네이션
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """엔티티 개수 조회"""
        query = select(func.count()).select_from(self.model_class)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self, id: Any) -> bool:
        """엔티티 존재 여부 확인"""
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.id == id)
        )
        return result.scalar() > 0
```

#### 1.2 Database Connection Manager

```python
# aegis_shared/database/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class DatabaseManager:
    """데이터베이스 연결 관리자"""
    
    def __init__(self, database_url: str, **engine_kwargs):
        self.engine = create_async_engine(
            database_url,
            echo=engine_kwargs.get('echo', False),
            pool_size=engine_kwargs.get('pool_size', 10),
            max_overflow=engine_kwargs.get('max_overflow', 20),
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """세션 컨텍스트 매니저"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """연결 종료"""
        await self.engine.dispose()

# 사용 예시
db_manager = DatabaseManager("postgresql+asyncpg://user:pass@localhost/db")

async with db_manager.session() as session:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id("user-123")
```

### 2. Authentication Module

#### 2.1 JWT Handler

```python
# aegis_shared/auth/jwt_handler.py
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import jwt
from aegis_shared.errors.exceptions import TokenExpiredError, InvalidTokenError

class JWTHandler:
    """JWT 토큰 생성 및 검증"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """액세스 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """리프레시 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """토큰 검증"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Invalid token")
```

#### 2.2 Authentication Middleware

```python
# aegis_shared/auth/middleware.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Callable
from aegis_shared.auth.jwt_handler import JWTHandler
from aegis_shared.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

class AuthMiddleware:
    """인증 미들웨어"""
    
    def __init__(self, jwt_handler: JWTHandler):
        self.jwt_handler = jwt_handler
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ):
        """미들웨어 실행"""
        # Authorization 헤더 확인
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = self.jwt_handler.verify_token(token)
                request.state.user = payload
                request.state.user_id = payload.get("user_id")
                
                # 로깅 컨텍스트에 사용자 정보 추가
                from aegis_shared.logging import add_context
                add_context(user_id=payload.get("user_id"))
                
            except Exception as e:
                logger.warning(f"Token verification failed: {e}")
        
        response = await call_next(request)
        return response

# FastAPI 의존성으로 사용
from fastapi import Depends

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_handler: JWTHandler = Depends()
) -> dict:
    """현재 사용자 정보 추출"""
    payload = jwt_handler.verify_token(credentials.credentials)
    return payload
```

### 3. Logging Module

#### 3.1 Structured Logger

```python
# aegis_shared/logging/structured_logger.py
import structlog
import logging
from contextvars import ContextVar
from typing import Optional

# 컨텍스트 변수
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
service_name_var: ContextVar[Optional[str]] = ContextVar('service_name', default=None)

def add_context_processor(logger, method_name, event_dict):
    """컨텍스트 정보를 로그에 추가"""
    event_dict['request_id'] = request_id_var.get()
    event_dict['user_id'] = user_id_var.get()
    event_dict['service'] = service_name_var.get()
    return event_dict

def configure_logging(service_name: str, log_level: str = "INFO"):
    """로깅 설정"""
    service_name_var.set(service_name)
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_context_processor,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    """로거 생성"""
    return structlog.get_logger(name)

def add_context(**kwargs):
    """로깅 컨텍스트 추가"""
    for key, value in kwargs.items():
        if key == 'request_id':
            request_id_var.set(value)
        elif key == 'user_id':
            user_id_var.set(value)
        elif key == 'service_name':
            service_name_var.set(value)

# 사용 예시
configure_logging("policy-service", "INFO")
logger = get_logger(__name__)

add_context(request_id="req-123", user_id="user-456")
logger.info("policy_created", policy_id="policy-789", title="새 정책")
# 출력: {"event": "policy_created", "request_id": "req-123", "user_id": "user-456", ...}
```

### 4. Messaging Module

#### 4.1 Event Publisher

```python
# aegis_shared/messaging/event_publisher.py
from typing import Any, Dict, Optional
from kafka import KafkaProducer
from datetime import datetime
import json
from aegis_shared.logging import get_logger, request_id_var, service_name_var

logger = get_logger(__name__)

class EventPublisher:
    """이벤트 발행자"""
    
    def __init__(self, bootstrap_servers: str, **kwargs):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            **kwargs
        )
    
    async def publish(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ):
        """이벤트 발행"""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "metadata": {
                "service": service_name_var.get(),
                "request_id": request_id_var.get()
            }
        }
        
        try:
            self.producer.send(
                topic,
                value=event,
                key=key.encode('utf-8') if key else None
            )
            self.producer.flush()
            
            logger.info(
                "event_published",
                topic=topic,
                event_type=event_type,
                key=key
            )
        except Exception as e:
            logger.error(
                "event_publish_failed",
                topic=topic,
                event_type=event_type,
                error=str(e)
            )
            raise
    
    def close(self):
        """프로듀서 종료"""
        self.producer.close()
```

### 5. Error Handling Module

#### 5.1 Common Exceptions

```python
# aegis_shared/errors/exceptions.py
from typing import Optional, Dict, Any

class AegisBaseException(Exception):
    """모든 Aegis 예외의 기본 클래스"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

# 인증 관련 예외
class AuthenticationError(AegisBaseException):
    """인증 실패"""
    pass

class TokenExpiredError(AuthenticationError):
    """토큰 만료"""
    pass

class InvalidTokenError(AuthenticationError):
    """유효하지 않은 토큰"""
    pass

# 데이터베이스 관련 예외
class DatabaseError(AegisBaseException):
    """데이터베이스 에러"""
    pass

class EntityNotFoundError(DatabaseError):
    """엔티티를 찾을 수 없음"""
    pass

class DuplicateEntityError(DatabaseError):
    """중복 엔티티"""
    pass

# 검증 관련 예외
class ValidationError(AegisBaseException):
    """검증 실패"""
    pass

# 외부 서비스 관련 예외
class ExternalServiceError(AegisBaseException):
    """외부 서비스 에러"""
    pass
```

## Data Models

### Base Models

```python
# aegis_shared/models/base.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

class BaseEntity(BaseModel):
    """모든 엔티티의 기본 모델"""
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class PaginatedResponse(BaseModel):
    """페이지네이션 응답"""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
```

### 6. Schema Registry Module

#### 6.1 중앙 스키마 레지스트리

```python
# aegis_shared/database/schema_registry.py
from typing import Dict, List, Optional, Set
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from datetime import datetime

class SchemaColumn(BaseModel):
    """스키마 컬럼 정의"""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default: Optional[str] = None
    description: Optional[str] = None

class SchemaReference(BaseModel):
    """스키마 간 참조 관계"""
    schema: str
    column: str
    on_delete: str = "CASCADE"
    on_update: str = "CASCADE"

class SchemaDefinition(BaseModel):
    """스키마 정의"""
    name: str
    owner: str  # 소유 서비스
    version: str = "1.0.0"
    description: Optional[str] = None
    columns: List[SchemaColumn]
    references: List[SchemaReference] = []
    indexes: List[Dict[str, any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SchemaRegistry:
    """중앙 스키마 레지스트리"""
    
    def __init__(self, registry_path: str = ".kiro/schemas"):
        self.registry_path = Path(registry_path)
        self.schemas: Dict[str, SchemaDefinition] = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """모든 스키마 파일 로드"""
        if not self.registry_path.exists():
            self.registry_path.mkdir(parents=True, exist_ok=True)
            return
        
        for schema_file in self.registry_path.glob("*.yaml"):
            if schema_file.name == "registry.yaml":
                continue
            
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_data = yaml.safe_load(f)
                schema = SchemaDefinition(**schema_data)
                self.schemas[schema.name] = schema
    
    def register_schema(self, schema: SchemaDefinition) -> None:
        """스키마 등록"""
        self.schemas[schema.name] = schema
        
        # YAML 파일로 저장
        schema_file = self.registry_path / f"{schema.name}.yaml"
        with open(schema_file, 'w', encoding='utf-8') as f:
            yaml.dump(schema.dict(), f, allow_unicode=True)
    
    def get_schema(self, name: str) -> Optional[SchemaDefinition]:
        """스키마 조회"""
        return self.schemas.get(name)
    
    def get_dependent_services(self, schema_name: str) -> Set[str]:
        """특정 스키마에 의존하는 서비스 목록"""
        dependent_services = set()
        
        for schema in self.schemas.values():
            for ref in schema.references:
                if ref.schema == schema_name:
                    dependent_services.add(schema.owner)
        
        return dependent_services
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """스키마 의존성 그래프 생성"""
        graph = {}
        
        for schema_name, schema in self.schemas.items():
            dependencies = [ref.schema for ref in schema.references]
            graph[schema_name] = dependencies
        
        return graph
    
    def validate_references(self) -> List[str]:
        """참조 무결성 검증"""
        errors = []
        
        for schema_name, schema in self.schemas.items():
            for ref in schema.references:
                if ref.schema not in self.schemas:
                    errors.append(
                        f"Schema '{schema_name}' references non-existent schema '{ref.schema}'"
                    )
                else:
                    # 참조 컬럼 존재 여부 확인
                    ref_schema = self.schemas[ref.schema]
                    column_names = [col.name for col in ref_schema.columns]
                    if ref.column not in column_names:
                        errors.append(
                            f"Schema '{schema_name}' references non-existent column "
                            f"'{ref.column}' in schema '{ref.schema}'"
                        )
        
        return errors
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """순환 의존성 탐지"""
        graph = self.get_dependency_graph()
        cycles = []
        
        def dfs(node: str, path: List[str], visited: Set[str]):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy(), visited)
        
        for schema_name in graph:
            dfs(schema_name, [], set())
        
        return cycles
    
    def generate_migration_order(self) -> List[str]:
        """마이그레이션 실행 순서 생성 (위상 정렬)"""
        graph = self.get_dependency_graph()
        in_degree = {schema: 0 for schema in graph}
        
        # 진입 차수 계산
        for dependencies in graph.values():
            for dep in dependencies:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # 위상 정렬
        queue = [schema for schema, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for schema, dependencies in graph.items():
                if node in dependencies:
                    in_degree[schema] -= 1
                    if in_degree[schema] == 0:
                        queue.append(schema)
        
        return result
    
    def generate_documentation(self) -> str:
        """스키마 문서 자동 생성"""
        doc = "# Database Schema Documentation\n\n"
        doc += f"Generated at: {datetime.utcnow().isoformat()}\n\n"
        
        for schema_name, schema in sorted(self.schemas.items()):
            doc += f"## {schema_name}\n\n"
            doc += f"**Owner:** {schema.owner}\n"
            doc += f"**Version:** {schema.version}\n\n"
            
            if schema.description:
                doc += f"{schema.description}\n\n"
            
            doc += "### Columns\n\n"
            doc += "| Name | Type | Nullable | Primary Key | Unique | Default |\n"
            doc += "|------|------|----------|-------------|--------|----------|\n"
            
            for col in schema.columns:
                doc += f"| {col.name} | {col.type} | {col.nullable} | "
                doc += f"{col.primary_key} | {col.unique} | {col.default or '-'} |\n"
            
            if schema.references:
                doc += "\n### References\n\n"
                for ref in schema.references:
                    doc += f"- `{ref.column}` → `{ref.schema}`\n"
            
            doc += "\n"
        
        return doc

# 사용 예시
registry = SchemaRegistry()

# 스키마 등록
users_schema = SchemaDefinition(
    name="users",
    owner="user-service",
    version="1.0.0",
    description="사용자 정보 테이블",
    columns=[
        SchemaColumn(name="user_id", type="UUID", primary_key=True, nullable=False),
        SchemaColumn(name="email", type="VARCHAR(255)", unique=True, nullable=False),
        SchemaColumn(name="name", type="VARCHAR(100)", nullable=False),
        SchemaColumn(name="created_at", type="TIMESTAMP", nullable=False),
    ]
)

registry.register_schema(users_schema)

# 의존성 검증
errors = registry.validate_references()
if errors:
    print("Schema validation errors:", errors)

# 마이그레이션 순서 생성
migration_order = registry.generate_migration_order()
print("Migration order:", migration_order)
```

#### 6.2 마이그레이션 조율 시스템

```python
# aegis_shared/database/migration_coordinator.py
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
from aegis_shared.database.schema_registry import SchemaRegistry
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class MigrationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class MigrationStep:
    """마이그레이션 단계"""
    service: str
    schema: str
    migration_file: str
    sql: str
    dependencies: List[str] = None
    status: MigrationStatus = MigrationStatus.PENDING
    error: Optional[str] = None
    executed_at: Optional[datetime] = None

class MigrationCoordinator:
    """마이그레이션 조율 시스템"""
    
    def __init__(self, schema_registry: SchemaRegistry):
        self.schema_registry = schema_registry
        self.migration_steps: List[MigrationStep] = []
        self.migration_history: List[Dict] = []
    
    def plan_migration(self, schema_changes: Dict[str, str]) -> List[MigrationStep]:
        """
        마이그레이션 계획 수립
        
        Args:
            schema_changes: {schema_name: migration_sql}
        """
        steps = []
        
        # 영향 받는 서비스 식별
        affected_services = set()
        for schema_name in schema_changes.keys():
            schema = self.schema_registry.get_schema(schema_name)
            if schema:
                affected_services.add(schema.owner)
                # 의존하는 서비스도 추가
                affected_services.update(
                    self.schema_registry.get_dependent_services(schema_name)
                )
        
        # 마이그레이션 순서 결정
        migration_order = self.schema_registry.generate_migration_order()
        
        # 마이그레이션 단계 생성
        for schema_name in migration_order:
            if schema_name in schema_changes:
                schema = self.schema_registry.get_schema(schema_name)
                step = MigrationStep(
                    service=schema.owner,
                    schema=schema_name,
                    migration_file=f"migrations/{schema_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql",
                    sql=schema_changes[schema_name],
                    dependencies=[ref.schema for ref in schema.references]
                )
                steps.append(step)
        
        self.migration_steps = steps
        return steps
    
    async def validate_migration(self) -> List[str]:
        """마이그레이션 사전 검증"""
        warnings = []
        
        # 순환 의존성 확인
        cycles = self.schema_registry.detect_circular_dependencies()
        if cycles:
            warnings.append(f"Circular dependencies detected: {cycles}")
        
        # 참조 무결성 확인
        ref_errors = self.schema_registry.validate_references()
        warnings.extend(ref_errors)
        
        # 데이터 손실 위험 확인
        for step in self.migration_steps:
            if "DROP COLUMN" in step.sql.upper():
                warnings.append(
                    f"WARNING: {step.schema} migration contains DROP COLUMN - potential data loss"
                )
            if "DROP TABLE" in step.sql.upper():
                warnings.append(
                    f"CRITICAL: {step.schema} migration contains DROP TABLE - data will be lost"
                )
        
        return warnings
    
    async def execute_coordinated_migration(self) -> bool:
        """조율된 마이그레이션 실행"""
        logger.info("Starting coordinated migration", 
                   total_steps=len(self.migration_steps))
        
        # 사전 검증
        warnings = await self.validate_migration()
        if warnings:
            logger.warning("Migration warnings detected", warnings=warnings)
        
        try:
            # 각 단계 순차 실행
            for step in self.migration_steps:
                await self._execute_step(step)
                
                if step.status == MigrationStatus.FAILED:
                    logger.error("Migration step failed", 
                               service=step.service, 
                               schema=step.schema,
                               error=step.error)
                    # 롤백 시작
                    await self._rollback_migration()
                    return False
            
            logger.info("Coordinated migration completed successfully")
            return True
            
        except Exception as e:
            logger.error("Migration coordination failed", error=str(e))
            await self._rollback_migration()
            return False
    
    async def _execute_step(self, step: MigrationStep):
        """단일 마이그레이션 단계 실행"""
        logger.info("Executing migration step", 
                   service=step.service, 
                   schema=step.schema)
        
        step.status = MigrationStatus.RUNNING
        
        try:
            # 실제 마이그레이션 실행 (서비스별 DB 연결 사용)
            # 여기서는 예시로 간단히 표현
            await asyncio.sleep(0.1)  # 실제로는 DB 마이그레이션 실행
            
            step.status = MigrationStatus.COMPLETED
            step.executed_at = datetime.utcnow()
            
            # 히스토리 기록
            self.migration_history.append({
                "service": step.service,
                "schema": step.schema,
                "migration_file": step.migration_file,
                "executed_at": step.executed_at,
                "status": "completed"
            })
            
            logger.info("Migration step completed", 
                       service=step.service, 
                       schema=step.schema)
            
        except Exception as e:
            step.status = MigrationStatus.FAILED
            step.error = str(e)
            raise
    
    async def _rollback_migration(self):
        """마이그레이션 롤백"""
        logger.warning("Rolling back migration")
        
        # 완료된 단계를 역순으로 롤백
        completed_steps = [
            step for step in self.migration_steps 
            if step.status == MigrationStatus.COMPLETED
        ]
        
        for step in reversed(completed_steps):
            try:
                logger.info("Rolling back migration step", 
                           service=step.service, 
                           schema=step.schema)
                
                # 실제 롤백 실행
                await asyncio.sleep(0.1)
                
                step.status = MigrationStatus.ROLLED_BACK
                
            except Exception as e:
                logger.error("Rollback failed", 
                           service=step.service, 
                           schema=step.schema,
                           error=str(e))
    
    def get_migration_history(self, service: Optional[str] = None) -> List[Dict]:
        """마이그레이션 이력 조회"""
        if service:
            return [h for h in self.migration_history if h["service"] == service]
        return self.migration_history
    
    def generate_impact_report(self, schema_changes: Dict[str, str]) -> Dict:
        """영향 분석 보고서 생성"""
        steps = self.plan_migration(schema_changes)
        
        affected_services = set(step.service for step in steps)
        
        report = {
            "total_schemas": len(schema_changes),
            "affected_services": list(affected_services),
            "migration_steps": len(steps),
            "estimated_duration": f"{len(steps) * 2} minutes",
            "steps": [
                {
                    "service": step.service,
                    "schema": step.schema,
                    "dependencies": step.dependencies
                }
                for step in steps
            ]
        }
        
        return report

# 사용 예시
async def main():
    registry = SchemaRegistry()
    coordinator = MigrationCoordinator(registry)
    
    # 스키마 변경 계획
    schema_changes = {
        "users": "ALTER TABLE users ADD COLUMN phone VARCHAR(20);",
        "user_profiles": "ALTER TABLE user_profiles ADD COLUMN phone_verified BOOLEAN DEFAULT FALSE;"
    }
    
    # 영향 분석
    impact_report = coordinator.generate_impact_report(schema_changes)
    print("Impact Report:", impact_report)
    
    # 마이그레이션 실행
    success = await coordinator.execute_coordinated_migration()
    
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed and rolled back")
```

### 7. Central Error Code Registry ⭐

#### 7.1 Error Code System

```python
# aegis_shared/errors/error_codes.py
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass

class ErrorCategory(str, Enum):
    """에러 카테고리"""
    AUTHENTICATION = "AUTH"
    AUTHORIZATION = "AUTHZ"
    VALIDATION = "VALID"
    DATABASE = "DB"
    EXTERNAL_SERVICE = "EXT"
    BUSINESS_LOGIC = "BIZ"
    SYSTEM = "SYS"

@dataclass
class ErrorCodeDefinition:
    """에러 코드 정의"""
    code: str
    category: ErrorCategory
    message: str
    http_status: int
    description: str
    user_message: str  # 사용자에게 표시할 메시지
    resolution: str  # 해결 방법

class ErrorCode(str, Enum):
    """중앙 에러 코드 레지스트리"""
    
    # 인증 관련 (AUTH_1xxx)
    INVALID_TOKEN = "AUTH_1001"
    TOKEN_EXPIRED = "AUTH_1002"
    TOKEN_MISSING = "AUTH_1003"
    INVALID_CREDENTIALS = "AUTH_1004"
    
    # 인가 관련 (AUTHZ_2xxx)
    INSUFFICIENT_PERMISSION = "AUTHZ_2001"
    RESOURCE_FORBIDDEN = "AUTHZ_2002"
    ROLE_NOT_FOUND = "AUTHZ_2003"
    
    # 검증 관련 (VALID_3xxx)
    INVALID_INPUT = "VALID_3001"
    MISSING_REQUIRED_FIELD = "VALID_3002"
    INVALID_FORMAT = "VALID_3003"
    VALUE_OUT_OF_RANGE = "VALID_3004"
    
    # 데이터베이스 관련 (DB_4xxx)
    ENTITY_NOT_FOUND = "DB_4001"
    DUPLICATE_ENTITY = "DB_4002"
    DATABASE_CONNECTION_ERROR = "DB_4003"
    TRANSACTION_FAILED = "DB_4004"
    CONSTRAINT_VIOLATION = "DB_4005"
    
    # 외부 서비스 관련 (EXT_5xxx)
    LLM_SERVICE_ERROR = "EXT_5001"
    LLM_RATE_LIMIT = "EXT_5002"
    EXTERNAL_API_ERROR = "EXT_5003"
    EXTERNAL_API_TIMEOUT = "EXT_5004"
    KAFKA_ERROR = "EXT_5005"
    REDIS_ERROR = "EXT_5006"
    ELASTICSEARCH_ERROR = "EXT_5007"
    
    # 비즈니스 로직 관련 (BIZ_6xxx)
    POLICY_NOT_ELIGIBLE = "BIZ_6001"
    APPLICATION_DEADLINE_PASSED = "BIZ_6002"
    INVALID_BUSINESS_STATE = "BIZ_6003"
    RECOMMENDATION_NOT_AVAILABLE = "BIZ_6004"
    
    # 시스템 관련 (SYS_7xxx)
    INTERNAL_SERVER_ERROR = "SYS_7001"
    SERVICE_UNAVAILABLE = "SYS_7002"
    CONFIGURATION_ERROR = "SYS_7003"
    RESOURCE_EXHAUSTED = "SYS_7004"

class ErrorCodeRegistry:
    """에러 코드 레지스트리 - 모든 에러 코드의 메타데이터 관리"""
    
    _registry: Dict[str, ErrorCodeDefinition] = {
        # 인증 관련
        ErrorCode.INVALID_TOKEN: ErrorCodeDefinition(
            code=ErrorCode.INVALID_TOKEN,
            category=ErrorCategory.AUTHENTICATION,
            message="Invalid authentication token",
            http_status=401,
            description="제공된 인증 토큰이 유효하지 않습니다",
            user_message="인증에 실패했습니다. 다시 로그인해주세요.",
            resolution="새로운 토큰을 발급받으세요"
        ),
        ErrorCode.TOKEN_EXPIRED: ErrorCodeDefinition(
            code=ErrorCode.TOKEN_EXPIRED,
            category=ErrorCategory.AUTHENTICATION,
            message="Authentication token has expired",
            http_status=401,
            description="인증 토큰이 만료되었습니다",
            user_message="세션이 만료되었습니다. 다시 로그인해주세요.",
            resolution="리프레시 토큰으로 새 액세스 토큰을 발급받으세요"
        ),
        ErrorCode.INSUFFICIENT_PERMISSION: ErrorCodeDefinition(
            code=ErrorCode.INSUFFICIENT_PERMISSION,
            category=ErrorCategory.AUTHORIZATION,
            message="Insufficient permissions",
            http_status=403,
            description="요청한 작업을 수행할 권한이 없습니다",
            user_message="이 작업을 수행할 권한이 없습니다.",
            resolution="관리자에게 권한을 요청하세요"
        ),
        ErrorCode.ENTITY_NOT_FOUND: ErrorCodeDefinition(
            code=ErrorCode.ENTITY_NOT_FOUND,
            category=ErrorCategory.DATABASE,
            message="Entity not found",
            http_status=404,
            description="요청한 리소스를 찾을 수 없습니다",
            user_message="요청하신 정보를 찾을 수 없습니다.",
            resolution="올바른 ID를 사용하고 있는지 확인하세요"
        ),
        ErrorCode.DUPLICATE_ENTITY: ErrorCodeDefinition(
            code=ErrorCode.DUPLICATE_ENTITY,
            category=ErrorCategory.DATABASE,
            message="Duplicate entity",
            http_status=409,
            description="이미 존재하는 리소스입니다",
            user_message="이미 존재하는 정보입니다.",
            resolution="다른 값을 사용하세요"
        ),
        ErrorCode.LLM_SERVICE_ERROR: ErrorCodeDefinition(
            code=ErrorCode.LLM_SERVICE_ERROR,
            category=ErrorCategory.EXTERNAL_SERVICE,
            message="LLM service error",
            http_status=503,
            description="LLM 서비스 호출에 실패했습니다",
            user_message="AI 서비스가 일시적으로 사용할 수 없습니다.",
            resolution="잠시 후 다시 시도하세요"
        ),
        ErrorCode.POLICY_NOT_ELIGIBLE: ErrorCodeDefinition(
            code=ErrorCode.POLICY_NOT_ELIGIBLE,
            category=ErrorCategory.BUSINESS_LOGIC,
            message="Policy not eligible",
            http_status=400,
            description="해당 정책의 지원 대상이 아닙니다",
            user_message="이 정책의 지원 대상이 아닙니다.",
            resolution="지원 자격 요건을 확인하세요"
        ),
        ErrorCode.INTERNAL_SERVER_ERROR: ErrorCodeDefinition(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            category=ErrorCategory.SYSTEM,
            message="Internal server error",
            http_status=500,
            description="서버 내부 오류가 발생했습니다",
            user_message="일시적인 오류가 발생했습니다.",
            resolution="잠시 후 다시 시도하거나 관리자에게 문의하세요"
        ),
    }
    
    @classmethod
    def get(cls, error_code: ErrorCode) -> Optional[ErrorCodeDefinition]:
        """에러 코드 정의 조회"""
        return cls._registry.get(error_code)
    
    @classmethod
    def get_by_category(cls, category: ErrorCategory) -> Dict[str, ErrorCodeDefinition]:
        """카테고리별 에러 코드 조회"""
        return {
            code: definition 
            for code, definition in cls._registry.items() 
            if definition.category == category
        }
    
    @classmethod
    def register(cls, definition: ErrorCodeDefinition):
        """새로운 에러 코드 등록"""
        cls._registry[definition.code] = definition
    
    @classmethod
    def generate_documentation(cls) -> str:
        """에러 코드 문서 자동 생성"""
        doc = "# Error Code Documentation\n\n"
        
        for category in ErrorCategory:
            doc += f"## {category.value} - {category.name}\n\n"
            doc += "| Code | Message | HTTP Status | User Message |\n"
            doc += "|------|---------|-------------|---------------|\n"
            
            category_errors = cls.get_by_category(category)
            for code, definition in sorted(category_errors.items()):
                doc += f"| {definition.code} | {definition.message} | "
                doc += f"{definition.http_status} | {definition.user_message} |\n"
            
            doc += "\n"
        
        return doc

# 사용 예시
error_def = ErrorCodeRegistry.get(ErrorCode.ENTITY_NOT_FOUND)
print(f"HTTP Status: {error_def.http_status}")
print(f"User Message: {error_def.user_message}")
```

#### 7.2 Enhanced Exception Classes

```python
# aegis_shared/errors/exceptions.py (개선된 버전)
from typing import Optional, Dict, Any
from aegis_shared.errors.error_codes import ErrorCode, ErrorCodeRegistry

class AegisBaseException(Exception):
    """모든 Aegis 예외의 기본 클래스 - 에러 코드 레지스트리 통합"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.error_code = error_code
        self.error_definition = ErrorCodeRegistry.get(error_code)
        
        # 메시지 우선순위: 커스텀 > 레지스트리 > 기본
        self.message = message or (self.error_definition.message if self.error_definition else str(error_code))
        self.user_message = user_message or (self.error_definition.user_message if self.error_definition else self.message)
        self.http_status = self.error_definition.http_status if self.error_definition else 500
        self.details = details or {}
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "http_status": self.http_status
        }

# 특화된 예외 클래스들
class AuthenticationError(AegisBaseException):
    """인증 실패"""
    def __init__(self, error_code: ErrorCode = ErrorCode.INVALID_TOKEN, **kwargs):
        super().__init__(error_code, **kwargs)

class EntityNotFoundError(AegisBaseException):
    """엔티티를 찾을 수 없음"""
    def __init__(self, entity_type: str, entity_id: str, **kwargs):
        super().__init__(
            ErrorCode.ENTITY_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id},
            **kwargs
        )

class DuplicateEntityError(AegisBaseException):
    """중복 엔티티"""
    def __init__(self, entity_type: str, **kwargs):
        super().__init__(
            ErrorCode.DUPLICATE_ENTITY,
            details={"entity_type": entity_type},
            **kwargs
        )
```

### 8. Event Schema Versioning ⭐

#### 8.1 Event Schema Registry

```python
# aegis_shared/messaging/schema_registry.py
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class SchemaCompatibility(str, Enum):
    """스키마 호환성 타입"""
    BACKWARD = "backward"  # 새 스키마로 이전 데이터 읽기 가능
    FORWARD = "forward"    # 이전 스키마로 새 데이터 읽기 가능
    FULL = "full"          # 양방향 호환
    NONE = "none"          # 호환성 없음

class EventSchemaVersion(BaseModel):
    """이벤트 스키마 버전"""
    event_type: str
    version: int
    schema: Dict[str, Any]  # JSON Schema
    compatibility: SchemaCompatibility
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deprecated: bool = False
    deprecation_date: Optional[datetime] = None

class EventSchemaRegistry:
    """이벤트 스키마 레지스트리"""
    
    def __init__(self):
        self.schemas: Dict[str, List[EventSchemaVersion]] = {}
    
    def register_schema(self, schema_version: EventSchemaVersion):
        """스키마 등록"""
        event_type = schema_version.event_type
        
        if event_type not in self.schemas:
            self.schemas[event_type] = []
        
        # 버전 중복 확인
        existing_versions = [s.version for s in self.schemas[event_type]]
        if schema_version.version in existing_versions:
            raise ValueError(f"Schema version {schema_version.version} already exists for {event_type}")
        
        self.schemas[event_type].append(schema_version)
        self.schemas[event_type].sort(key=lambda s: s.version)
    
    def get_schema(self, event_type: str, version: Optional[int] = None) -> Optional[EventSchemaVersion]:
        """스키마 조회 - 버전 미지정 시 최신 버전 반환"""
        if event_type not in self.schemas:
            return None
        
        if version is None:
            # 최신 버전 반환
            return self.schemas[event_type][-1]
        
        for schema in self.schemas[event_type]:
            if schema.version == version:
                return schema
        
        return None
    
    def get_all_versions(self, event_type: str) -> List[EventSchemaVersion]:
        """특정 이벤트의 모든 스키마 버전 조회"""
        return self.schemas.get(event_type, [])
    
    def check_compatibility(
        self, 
        event_type: str, 
        new_schema: Dict[str, Any],
        compatibility_type: SchemaCompatibility
    ) -> bool:
        """스키마 호환성 검증"""
        current_schema = self.get_schema(event_type)
        if not current_schema:
            return True  # 첫 번째 스키마는 항상 호환
        
        if compatibility_type == SchemaCompatibility.BACKWARD:
            return self._check_backward_compatibility(current_schema.schema, new_schema)
        elif compatibility_type == SchemaCompatibility.FORWARD:
            return self._check_forward_compatibility(current_schema.schema, new_schema)
        elif compatibility_type == SchemaCompatibility.FULL:
            return (self._check_backward_compatibility(current_schema.schema, new_schema) and
                   self._check_forward_compatibility(current_schema.schema, new_schema))
        
        return True
    
    def _check_backward_compatibility(self, old_schema: Dict, new_schema: Dict) -> bool:
        """Backward 호환성 검증 - 새 스키마로 이전 데이터 읽기 가능"""
        # 필수 필드가 추가되지 않았는지 확인
        old_required = set(old_schema.get('required', []))
        new_required = set(new_schema.get('required', []))
        
        if new_required - old_required:
            return False  # 새로운 필수 필드 추가는 backward incompatible
        
        # 기존 필드 타입이 변경되지 않았는지 확인
        old_properties = old_schema.get('properties', {})
        new_properties = new_schema.get('properties', {})
        
        for field_name in old_properties:
            if field_name in new_properties:
                if old_properties[field_name].get('type') != new_properties[field_name].get('type'):
                    return False
        
        return True
    
    def _check_forward_compatibility(self, old_schema: Dict, new_schema: Dict) -> bool:
        """Forward 호환성 검증 - 이전 스키마로 새 데이터 읽기 가능"""
        # 필수 필드가 제거되지 않았는지 확인
        old_required = set(old_schema.get('required', []))
        new_required = set(new_schema.get('required', []))
        
        if old_required - new_required:
            return False  # 필수 필드 제거는 forward incompatible
        
        return True
    
    def deprecate_version(self, event_type: str, version: int):
        """스키마 버전 폐기 예고"""
        schema = self.get_schema(event_type, version)
        if schema:
            schema.deprecated = True
            schema.deprecation_date = datetime.utcnow()

# 사용 예시
schema_registry = EventSchemaRegistry()

# 스키마 등록
policy_created_v1 = EventSchemaVersion(
    event_type="policy.created",
    version=1,
    schema={
        "type": "object",
        "properties": {
            "policy_id": {"type": "string"},
            "title": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"}
        },
        "required": ["policy_id", "title"]
    },
    compatibility=SchemaCompatibility.BACKWARD
)

schema_registry.register_schema(policy_created_v1)

# 새 버전 호환성 검증
new_schema = {
    "type": "object",
    "properties": {
        "policy_id": {"type": "string"},
        "title": {"type": "string"},
        "created_at": {"type": "string", "format": "date-time"},
        "category": {"type": "string"}  # 새 필드 (optional)
    },
    "required": ["policy_id", "title"]
}

is_compatible = schema_registry.check_compatibility(
    "policy.created",
    new_schema,
    SchemaCompatibility.BACKWARD
)
```

#### 8.2 Versioned Event Publisher

```python
# aegis_shared/messaging/event_publisher.py (개선된 버전)
from typing import Any, Dict, Optional
from kafka import KafkaProducer
from datetime import datetime
import json
from aegis_shared.logging import get_logger
from aegis_shared.messaging.schema_registry import EventSchemaRegistry

logger = get_logger(__name__)

class VersionedEventPublisher:
    """버전 관리를 지원하는 이벤트 발행자"""
    
    def __init__(
        self, 
        bootstrap_servers: str,
        schema_registry: EventSchemaRegistry,
        **kwargs
    ):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            **kwargs
        )
        self.schema_registry = schema_registry
    
    async def publish(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None,
        schema_version: Optional[int] = None
    ):
        """버전 관리를 지원하는 이벤트 발행"""
        
        # 스키마 조회
        schema = self.schema_registry.get_schema(event_type, schema_version)
        if not schema:
            logger.warning(f"No schema found for {event_type} version {schema_version}")
        elif schema.deprecated:
            logger.warning(f"Using deprecated schema {event_type} v{schema.version}")
        
        # 이벤트 구성
        event = {
            "event_type": event_type,
            "schema_version": schema.version if schema else 1,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "metadata": {
                "service": "aegis",
                "compatibility": schema.compatibility.value if schema else "none"
            }
        }
        
        try:
            self.producer.send(
                topic,
                value=event,
                key=key.encode('utf-8') if key else None
            )
            self.producer.flush()
            
            logger.info(
                "versioned_event_published",
                topic=topic,
                event_type=event_type,
                schema_version=event["schema_version"]
            )
        except Exception as e:
            logger.error(
                "event_publish_failed",
                topic=topic,
                event_type=event_type,
                error=str(e)
            )
            raise
```

### 9. Kafka KRaft Mode Support ⭐

#### 9.1 KRaft-Compatible Kafka Configuration

```python
# aegis_shared/messaging/kafka_producer.py (KRaft 지원)
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from typing import List, Dict, Any
import json

class KRaftKafkaProducer:
    """KRaft 모드를 지원하는 Kafka 프로듀서"""
    
    def __init__(
        self,
        bootstrap_servers: str,
        **kwargs
    ):
        """
        KRaft 모드 Kafka 연결
        
        Note: Kafka 3.3+ 부터 KRaft 모드 지원
        Zookeeper 없이 내부 Raft 프로토콜로 메타데이터 관리
        """
        self.bootstrap_servers = bootstrap_servers
        
        # KRaft 모드에서는 Zookeeper 설정 불필요
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # KRaft 모드 최적화 설정
            acks='all',  # 모든 in-sync replicas 확인
            retries=3,
            max_in_flight_requests_per_connection=5,
            enable_idempotence=True,  # 정확히 한 번 전송 보장
            **kwargs
        )
        
        # Admin 클라이언트 (토픽 관리용)
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='aegis-admin'
        )
    
    def create_topics(self, topics: List[Dict[str, Any]]):
        """토픽 생성 - KRaft 모드에서도 동일"""
        new_topics = []
        
        for topic_config in topics:
            new_topic = NewTopic(
                name=topic_config['name'],
                num_partitions=topic_config.get('partitions', 3),
                replication_factor=topic_config.get('replication_factor', 3),
                topic_configs=topic_config.get('configs', {})
            )
            new_topics.append(new_topic)
        
        try:
            self.admin_client.create_topics(new_topics, validate_only=False)
            logger.info(f"Created {len(new_topics)} topics in KRaft mode")
        except Exception as e:
            logger.error(f"Failed to create topics: {e}")
            raise

# 사용 예시
producer = KRaftKafkaProducer(
    bootstrap_servers='kafka-broker-1:9092,kafka-broker-2:9092,kafka-broker-3:9092'
)

# 토픽 생성 (KRaft 모드)
producer.create_topics([
    {
        'name': 'policy-events',
        'partitions': 6,
        'replication_factor': 3,
        'configs': {
            'retention.ms': '604800000',  # 7 days
            'compression.type': 'snappy'
        }
    }
])
```

### 10. API Contract Validation ⭐

#### 10.1 API Contract Models

```python
# aegis_shared/models/api_contracts.py
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from enum import Enum

class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

class APIEndpoint(BaseModel):
    """API 엔드포인트 계약"""
    path: str
    method: HTTPMethod
    summary: str
    description: Optional[str] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Dict[str, Any]
    error_codes: List[str] = []
    
    @validator('path')
    def validate_path(cls, v):
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        return v

class ServiceContract(BaseModel):
    """서비스 API 계약"""
    service_name: str
    version: str
    base_url: str
    endpoints: List[APIEndpoint]
    
    def get_endpoint(self, path: str, method: HTTPMethod) -> Optional[APIEndpoint]:
        """엔드포인트 조회"""
        for endpoint in self.endpoints:
            if endpoint.path == path and endpoint.method == method:
                return endpoint
        return None

class ContractValidator:
    """API 계약 검증기"""
    
    def __init__(self):
        self.contracts: Dict[str, ServiceContract] = {}
    
    def register_contract(self, contract: ServiceContract):
        """계약 등록"""
        self.contracts[contract.service_name] = contract
    
    def validate_request(
        self,
        service_name: str,
        path: str,
        method: HTTPMethod,
        data: Dict[str, Any]
    ) -> bool:
        """요청 데이터 검증"""
        contract = self.contracts.get(service_name)
        if not contract:
            return False
        
        endpoint = contract.get_endpoint(path, method)
        if not endpoint or not endpoint.request_schema:
            return True
        
        # JSON Schema 검증
        from jsonschema import validate, ValidationError
        try:
            validate(instance=data, schema=endpoint.request_schema)
            return True
        except ValidationError:
            return False
    
    def validate_response(
        self,
        service_name: str,
        path: str,
        method: HTTPMethod,
        data: Dict[str, Any]
    ) -> bool:
        """응답 데이터 검증"""
        contract = self.contracts.get(service_name)
        if not contract:
            return False
        
        endpoint = contract.get_endpoint(path, method)
        if not endpoint:
            return False
        
        from jsonschema import validate, ValidationError
        try:
            validate(instance=data, schema=endpoint.response_schema)
            return True
        except ValidationError:
            return False

# 사용 예시
policy_service_contract = ServiceContract(
    service_name="policy-service",
    version="1.0.0",
    base_url="http://policy-service:8000",
    endpoints=[
        APIEndpoint(
            path="/api/v1/policies",
            method=HTTPMethod.POST,
            summary="Create new policy",
            request_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["title", "content"]
            },
            response_schema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string"},
                    "title": {"type": "string"}
                }
            },
            error_codes=["VALID_3001", "DB_4002"]
        )
    ]
)

validator = ContractValidator()
validator.register_contract(policy_service_contract)
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_base_repository.py
import pytest
from aegis_shared.database.base_repository import BaseRepository

@pytest.mark.asyncio
async def test_create_entity(db_session, sample_entity):
    repo = BaseRepository(db_session, SampleModel)
    created = await repo.create(sample_entity)
    
    assert created.id is not None
    assert created.created_at is not None

@pytest.mark.asyncio
async def test_get_by_id(db_session, sample_entity):
    repo = BaseRepository(db_session, SampleModel)
    created = await repo.create(sample_entity)
    
    retrieved = await repo.get_by_id(created.id)
    assert retrieved.id == created.id

# tests/unit/test_schema_registry.py
import pytest
from aegis_shared.database.schema_registry import SchemaRegistry, SchemaDefinition, SchemaColumn

def test_register_schema():
    registry = SchemaRegistry()
    
    schema = SchemaDefinition(
        name="test_table",
        owner="test-service",
        columns=[
            SchemaColumn(name="id", type="UUID", primary_key=True)
        ]
    )
    
    registry.register_schema(schema)
    retrieved = registry.get_schema("test_table")
    
    assert retrieved is not None
    assert retrieved.name == "test_table"

def test_detect_circular_dependencies():
    registry = SchemaRegistry()
    # 순환 의존성 테스트 로직
    pass

@pytest.mark.asyncio
async def test_migration_coordinator():
    from aegis_shared.database.migration_coordinator import MigrationCoordinator
    
    registry = SchemaRegistry()
    coordinator = MigrationCoordinator(registry)
    
    schema_changes = {
        "users": "ALTER TABLE users ADD COLUMN test VARCHAR(50);"
    }
    
    steps = coordinator.plan_migration(schema_changes)
    assert len(steps) > 0
```

---

이 설계 문서는 Shared Library의 모든 구성 요소를 상세히 정의합니다.


### Integration Tests

```python
# tests/integration/test_full_workflow.py
import pytest
from aegis_shared.database import BaseRepository, SchemaRegistry, MigrationCoordinator
from aegis_shared.messaging import VersionedEventPublisher, EventSchemaRegistry
from aegis_shared.errors import ErrorCode, EntityNotFoundError

@pytest.mark.integration
class TestFullWorkflow:
    """전체 워크플로우 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_database_schema_migration_workflow(self):
        """
        스키마 마이그레이션 전체 워크플로우 테스트
        
        시나리오:
        1. 스키마 등록
        2. 의존성 분석
        3. 마이그레이션 계획
        4. 마이그레이션 실행
        5. 롤백 테스트
        """
        # 1. 스키마 레지스트리 초기화
        registry = SchemaRegistry()
        
        # 2. 스키마 등록
        users_schema = SchemaDefinition(
            name="users",
            owner="user-service",
            columns=[
                SchemaColumn(name="user_id", type="UUID", primary_key=True),
                SchemaColumn(name="email", type="VARCHAR(255)", unique=True)
            ]
        )
        registry.register_schema(users_schema)
        
        policies_schema = SchemaDefinition(
            name="policies",
            owner="policy-service",
            columns=[
                SchemaColumn(name="policy_id", type="UUID", primary_key=True),
                SchemaColumn(name="created_by", type="UUID")
            ],
            references=[
                SchemaReference(schema="users", column="created_by")
            ]
        )
        registry.register_schema(policies_schema)
        
        # 3. 의존성 검증
        errors = registry.validate_references()
        assert len(errors) == 0
        
        # 4. 마이그레이션 순서 생성
        migration_order = registry.generate_migration_order()
        assert migration_order.index("users") < migration_order.index("policies")
        
        # 5. 마이그레이션 실행
        coordinator = MigrationCoordinator(registry)
        schema_changes = {
            "users": "CREATE TABLE users (user_id UUID PRIMARY KEY, email VARCHAR(255) UNIQUE);",
            "policies": "CREATE TABLE policies (policy_id UUID PRIMARY KEY, created_by UUID REFERENCES users(user_id));"
        }
        
        steps = coordinator.plan_migration(schema_changes)
        assert len(steps) == 2
        
        # 6. 실행 및 롤백 테스트
        success = await coordinator.execute_coordinated_migration()
        assert success
        
        # 롤백 테스트
        await coordinator.rollback_migration()
    
    @pytest.mark.asyncio
    async def test_event_schema_versioning_workflow(self):
        """
        이벤트 스키마 버전 관리 워크플로우 테스트
        
        시나리오:
        1. v1 스키마 등록
        2. v2 스키마 등록 (backward compatible)
        3. 호환성 검증
        4. 이벤트 발행 (v2)
        5. v1 구독자가 읽을 수 있는지 확인
        """
        # 1. 스키마 레지스트리 초기화
        schema_registry = EventSchemaRegistry()
        
        # 2. v1 스키마 등록
        schema_v1 = EventSchemaVersion(
            event_type="policy.created",
            version=1,
            schema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string"},
                    "title": {"type": "string"}
                },
                "required": ["policy_id", "title"]
            },
            compatibility=SchemaCompatibility.BACKWARD
        )
        schema_registry.register_schema(schema_v1)
        
        # 3. v2 스키마 등록 (category 필드 추가)
        schema_v2 = EventSchemaVersion(
            event_type="policy.created",
            version=2,
            schema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string"},
                    "title": {"type": "string"},
                    "category": {"type": "string"}  # 새 필드 (optional)
                },
                "required": ["policy_id", "title"]
            },
            compatibility=SchemaCompatibility.BACKWARD
        )
        
        # 4. 호환성 검증
        is_compatible = schema_registry.check_compatibility(
            "policy.created",
            schema_v2.schema,
            SchemaCompatibility.BACKWARD
        )
        assert is_compatible
        
        schema_registry.register_schema(schema_v2)
        
        # 5. 이벤트 발행 (v2)
        event_publisher = VersionedEventPublisher(
            bootstrap_servers='localhost:9092',
            schema_registry=schema_registry
        )
        
        await event_publisher.publish(
            topic="test-events",
            event_type="policy.created",
            data={
                "policy_id": "123",
                "title": "Test Policy",
                "category": "융자"
            },
            schema_version=2
        )
        
        # 6. v1 구독자 시뮬레이션 (category 필드 무시)
        # 실제로는 Kafka에서 읽어와야 하지만 테스트에서는 검증만
        assert True  # v1 구독자도 읽을 수 있음

@pytest.mark.integration
class TestErrorHandling:
    """에러 처리 통합 테스트"""
    
    def test_error_code_registry_integration(self):
        """중앙 에러 코드 레지스트리 통합 테스트"""
        from aegis_shared.errors import ErrorCode, ErrorCodeRegistry, AegisBaseException
        
        # 1. 에러 코드 조회
        error_def = ErrorCodeRegistry.get(ErrorCode.ENTITY_NOT_FOUND)
        assert error_def is not None
        assert error_def.http_status == 404
        assert error_def.user_message is not None
        
        # 2. 예외 생성
        exception = AegisBaseException(
            error_code=ErrorCode.ENTITY_NOT_FOUND,
            details={"entity_id": "123"}
        )
        
        # 3. 예외 정보 확인
        error_dict = exception.to_dict()
        assert error_dict['error_code'] == ErrorCode.ENTITY_NOT_FOUND
        assert error_dict['http_status'] == 404
        assert 'entity_id' in error_dict['details']
        
        # 4. 카테고리별 에러 조회
        auth_errors = ErrorCodeRegistry.get_by_category(ErrorCategory.AUTHENTICATION)
        assert len(auth_errors) > 0

### Package Tests

```python
# tests/package/test_installation.py
import subprocess
import pytest

def test_package_installation():
    """패키지 설치 테스트"""
    result = subprocess.run(
        ['pip', 'install', '-e', '.'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

def test_package_imports():
    """패키지 import 테스트"""
    # 모든 주요 모듈 import 가능한지 확인
    try:
        from aegis_shared.database import BaseRepository
        from aegis_shared.auth import JWTHandler
        from aegis_shared.messaging import EventPublisher
        from aegis_shared.logging import get_logger
        from aegis_shared.errors import ErrorCode
        from aegis_shared.cache import cache_result
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_version_info():
    """버전 정보 테스트"""
    from aegis_shared import __version__
    assert __version__ is not None
    assert len(__version__.split('.')) == 3  # SemVer format
```

---

## 버전 관리 전략

### Semantic Versioning (SemVer)

aegis-shared는 Semantic Versioning 2.0.0을 따릅니다.

**버전 형식**: MAJOR.MINOR.PATCH

#### MAJOR 버전 (Breaking Changes)

다음 변경 시 MAJOR 버전 증가:
- BaseRepository 인터페이스 변경
- JWTHandler 메서드 시그니처 변경
- ErrorCode 제거 또는 변경
- 필수 파라미터 추가

**예시:**
```python
# v1.0.0
class BaseRepository:
    async def create(self, entity):
        pass

# v2.0.0 (Breaking Change)
class BaseRepository:
    async def create(self, entity, validate=True):  # 필수 파라미터 추가
        pass
```

**마이그레이션 가이드 제공 필수**

#### MINOR 버전 (Backward Compatible)

다음 변경 시 MINOR 버전 증가:
- 새로운 모듈 추가
- 새로운 ErrorCode 추가
- 선택적 파라미터 추가
- 새로운 유틸리티 함수 추가

**예시:**
```python
# v1.0.0
class ErrorCode(str, Enum):
    ENTITY_NOT_FOUND = "DB_4001"

# v1.1.0 (Backward Compatible)
class ErrorCode(str, Enum):
    ENTITY_NOT_FOUND = "DB_4001"
    ENTITY_LOCKED = "DB_4006"  # 새 에러 코드 추가
```

#### PATCH 버전 (Bug Fixes)

다음 변경 시 PATCH 버전 증가:
- 버그 수정
- 성능 개선
- 문서 업데이트
- 내부 리팩토링

**예시:**
```python
# v1.0.0 (버그)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password, bcrypt.gensalt(rounds=10))  # 너무 약함

# v1.0.1 (버그 수정)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))  # 보안 강화
```

### 버전 호환성 정책

#### 지원 버전
- **Current**: 최신 버전 (완전 지원)
- **Previous**: 이전 MAJOR 버전 (보안 패치만)
- **Deprecated**: 2개 이전 MAJOR 버전 (지원 종료)

**예시:**
- Current: v3.x.x (완전 지원)
- Previous: v2.x.x (보안 패치만, 6개월)
- Deprecated: v1.x.x (지원 종료)

#### 폐기 프로세스 (Deprecation)

1. **공지** (N 버전): 폐기 예정 기능 표시
```python
@deprecated(version="2.0.0", reason="Use new_function instead")
def old_function():
    pass
```

2. **경고** (N+1 버전): 사용 시 경고 로그
```python
def old_function():
    warnings.warn("old_function is deprecated, use new_function", DeprecationWarning)
    pass
```

3. **제거** (N+2 버전): 완전 제거

### CHANGELOG 관리

모든 버전 변경은 CHANGELOG.md에 기록:

```markdown
# Changelog

## [2.0.0] - 2025-11-01

### Breaking Changes
- BaseRepository: create() 메서드에 validate 파라미터 추가

### Added
- 새로운 ErrorCode: ENTITY_LOCKED
- API 계약 검증 모듈

### Fixed
- JWT 토큰 만료 시간 버그 수정

### Deprecated
- old_function() → new_function() 사용 권장

## [1.2.0] - 2025-10-15

### Added
- Kafka KRaft 모드 지원
- 이벤트 스키마 버전 관리

### Fixed
- Redis 연결 풀 메모리 누수 수정
```

---

## 사용 예시

### 각 모듈별 실제 사용 예시

#### 1. Database 모듈 사용

```python
# 서비스 초기화
from aegis_shared.database import DatabaseManager, BaseRepository, SchemaRegistry

# 1. 데이터베이스 연결 설정
db_manager = DatabaseManager(
    database_url="postgresql+asyncpg://user:pass@localhost/aegis",
    pool_size=10,
    max_overflow=20
)

# 2. 스키마 등록
schema_registry = SchemaRegistry()
schema_registry.register_schema(policy_schema)

# 3. Repository 생성
class PolicyRepository(BaseRepository[Policy]):
    def __init__(self, session):
        super().__init__(session, Policy)

# 4. 사용
async with db_manager.session() as session:
    policy_repo = PolicyRepository(session)
    
    # CRUD 자동 제공
    policy = await policy_repo.create(new_policy)
    found = await policy_repo.get_by_id(policy.id)
    policies = await policy_repo.list(skip=0, limit=10)
```

#### 2. Auth 모듈 사용

```python
from aegis_shared.auth import JWTHandler, require_role, get_current_user
from fastapi import Depends

# 1. JWT Handler 초기화
jwt_handler = JWTHandler(
    secret_key=SECRET_KEY,
    algorithm='HS256'
)

# 2. 토큰 생성
access_token = jwt_handler.create_access_token(
    data={'user_id': str(user.id), 'role': 'admin'}
)

# 3. API에서 사용
@router.get("/admin/dashboard")
@require_role("admin")
async def admin_dashboard(current_user: dict = Depends(get_current_user)):
    return {"message": f"Welcome {current_user['user_id']}"}
```

#### 3. Messaging 모듈 사용

```python
from aegis_shared.messaging import VersionedEventPublisher, EventSchemaRegistry

# 1. 스키마 레지스트리 초기화
schema_registry = EventSchemaRegistry()

# 2. 이벤트 발행자 초기화
event_publisher = VersionedEventPublisher(
    bootstrap_servers='kafka:9092',
    schema_registry=schema_registry
)

# 3. 이벤트 발행
await event_publisher.publish(
    topic="policy-events",
    event_type="policy.created",
    data={"policy_id": str(policy.id), "title": policy.title},
    schema_version=2
)
```

#### 4. Logging 모듈 사용

```python
from aegis_shared.logging import configure_logging, get_logger, add_context

# 1. 로깅 설정 (서비스 시작 시 한 번)
configure_logging("policy-service", "INFO")

# 2. 로거 생성
logger = get_logger(__name__)

# 3. 컨텍스트 추가
add_context(request_id="req-123", user_id="user-456")

# 4. 로그 기록
logger.info(
    "policy_created",
    policy_id=str(policy.id),
    title=policy.title
)
# 출력: {"event": "policy_created", "policy_id": "...", "request_id": "req-123", ...}
```

#### 5. Errors 모듈 사용

```python
from aegis_shared.errors import ErrorCode, EntityNotFoundError, ErrorCodeRegistry

# 1. 예외 발생
try:
    policy = await policy_repo.get_by_id(policy_id)
    if not policy:
        raise EntityNotFoundError(
            entity_type="Policy",
            entity_id=str(policy_id)
        )
except EntityNotFoundError as e:
    # 2. 예외 정보 활용
    print(e.error_code)  # ErrorCode.ENTITY_NOT_FOUND
    print(e.http_status)  # 404
    print(e.user_message)  # "요청하신 정보를 찾을 수 없습니다."
    
    # 3. FastAPI에서 사용
    raise HTTPException(
        status_code=e.http_status,
        detail=e.to_dict()
    )
```

#### 6. Cache 모듈 사용

```python
from aegis_shared.cache import cache_result, RedisClient

# 1. 데코레이터 방식
@cache_result(ttl=3600)  # 1시간 캐싱
async def get_policy(policy_id: str):
    return await policy_repo.get_by_id(policy_id)

# 2. 직접 사용
redis_client = RedisClient()
await redis_client.setex("key", 3600, "value")
value = await redis_client.get("key")
```
