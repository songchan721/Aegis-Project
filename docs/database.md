# 데이터베이스 (Database)

Aegis Shared Library의 데이터베이스 모듈은 일관된 데이터베이스 접근 패턴과 Repository 패턴을 제공합니다.

## 주요 구성 요소

### 1. Database Manager

데이터베이스 연결과 세션 관리를 담당합니다.

```python
from aegis_shared.database import DatabaseManager

# 데이터베이스 매니저 초기화
db_manager = DatabaseManager(
    database_url="postgresql+asyncpg://user:password@localhost/dbname",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30
)

# 세션 사용 (컨텍스트 매니저)
async with db_manager.session() as session:
    # 데이터베이스 작업 수행
    result = await session.execute("SELECT * FROM users")
    users = result.fetchall()
    
    # 자동으로 커밋됨
    # 예외 발생 시 자동으로 롤백됨

# 매니저 종료
await db_manager.close()
```

### 2. Base Repository

모든 Repository가 상속받는 기본 클래스로 CRUD 작업을 제공합니다.

```python
from aegis_shared.database import BaseRepository
from aegis_shared.models import BaseEntity
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 엔티티 정의
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

# Repository 정의
class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(self) -> List[User]:
        """활성 사용자 목록 조회"""
        return await self.list(filters={"deleted_at": None})

# 사용 예시
async with db_manager.session() as session:
    user_repo = UserRepository(session)
    
    # 생성
    new_user = User(email="user@example.com", name="John Doe")
    created_user = await user_repo.create(new_user)
    
    # 조회
    user = await user_repo.get_by_id(created_user.id)
    user_by_email = await user_repo.get_by_email("user@example.com")
    
    # 업데이트
    updated_user = await user_repo.update(user.id, name="Jane Doe")
    
    # 목록 조회 (페이지네이션)
    users = await user_repo.list(skip=0, limit=10)
    
    # 필터링
    active_users = await user_repo.get_active_users()
    
    # 개수 조회
    total_count = await user_repo.count()
    
    # 소프트 삭제
    await user_repo.soft_delete(user.id)
    
    # 하드 삭제
    await user_repo.delete(user.id)
```

### 3. Transaction Manager

트랜잭션 관리를 위한 유틸리티입니다.

```python
from aegis_shared.database import TransactionManager

async with db_manager.session() as session:
    transaction_manager = TransactionManager(session)
    
    # 트랜잭션 사용
    async with transaction_manager.transaction():
        user_repo = UserRepository(session)
        policy_repo = PolicyRepository(session)
        
        # 여러 작업을 하나의 트랜잭션으로 묶음
        user = await user_repo.create(User(email="user@example.com"))
        policy = await policy_repo.create(Policy(user_id=user.id, title="New Policy"))
        
        # 모든 작업이 성공하면 커밋
        # 하나라도 실패하면 롤백
```

### 4. Database Retry

데이터베이스 연결 오류 시 자동 재시도 기능입니다.

```python
from aegis_shared.database import with_db_retry

@with_db_retry(max_attempts=3, backoff_factor=2)
async def create_user_with_retry(user_data: dict):
    async with db_manager.session() as session:
        user_repo = UserRepository(session)
        return await user_repo.create(User(**user_data))

# 사용
try:
    user = await create_user_with_retry({
        "email": "user@example.com",
        "name": "John Doe"
    })
except DatabaseConnectionError:
    print("데이터베이스 연결에 실패했습니다")
```

## 고급 기능

### 1. 복잡한 쿼리

```python
from sqlalchemy import select, join, func, and_, or_

class UserRepository(BaseRepository[User]):
    async def get_users_with_policies(self, limit: int = 10):
        """정책을 가진 사용자 조회"""
        query = (
            select(User, func.count(Policy.id).label('policy_count'))
            .join(Policy, User.id == Policy.user_id)
            .group_by(User.id)
            .having(func.count(Policy.id) > 0)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return result.all()
    
    async def search_users(self, search_term: str, filters: dict = None):
        """사용자 검색"""
        query = select(User)
        
        # 검색 조건
        if search_term:
            search_filter = or_(
                User.name.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%")
            )
            query = query.where(search_filter)
        
        # 추가 필터
        if filters:
            if filters.get("active_only"):
                query = query.where(User.deleted_at.is_(None))
            
            if filters.get("created_after"):
                query = query.where(User.created_at >= filters["created_after"])
        
        result = await self.session.execute(query)
        return result.scalars().all()
```

### 2. 배치 작업

```python
class UserRepository(BaseRepository[User]):
    async def create_users_batch(self, users_data: List[dict]) -> List[User]:
        """사용자 배치 생성"""
        users = [User(**data) for data in users_data]
        return await self.create_many(users)
    
    async def update_users_batch(self, updates: List[dict]):
        """사용자 배치 업데이트"""
        for update_data in updates:
            user_id = update_data.pop("id")
            await self.session.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
        
        await self.session.flush()
```

### 3. 관계 처리

```python
from sqlalchemy.orm import relationship, selectinload

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    name = Column(String(100))
    
    # 관계 정의
    policies = relationship("Policy", back_populates="user")

class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    
    # 관계 정의
    user = relationship("User", back_populates="policies")

class UserRepository(BaseRepository[User]):
    async def get_user_with_policies(self, user_id: int) -> Optional[User]:
        """사용자와 정책을 함께 조회 (N+1 문제 방지)"""
        query = (
            select(User)
            .options(selectinload(User.policies))
            .where(User.id == user_id)
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
```

## 설정

### 환경 변수

```bash
# 데이터베이스 연결
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# 연결 풀 설정
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# 재시도 설정
DATABASE_RETRY_ATTEMPTS=3
DATABASE_RETRY_BACKOFF=2
```

### 설정 클래스

```python
from aegis_shared.config import Settings

settings = Settings()

db_manager = DatabaseManager(
    database_url=settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle
)
```

## 마이그레이션

### Alembic 설정

```python
# alembic/env.py
from aegis_shared.models import Base
from aegis_shared.config import Settings

settings = Settings()

# Alembic 설정
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

### 마이그레이션 명령

```bash
# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add user table"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```

## 에러 처리

```python
from aegis_shared.errors.exceptions import (
    DatabaseError,
    EntityNotFoundError,
    DuplicateEntityError
)

try:
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundError("User", user_id)
        
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise
except DuplicateEntityError as e:
    logger.warning(f"Duplicate entity: {e}")
    raise
```

## 테스트

### 테스트 데이터베이스 설정

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def test_db():
    """테스트용 데이터베이스 설정"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 세션 팩토리 생성
    session_factory = sessionmaker(engine, class_=AsyncSession)
    
    yield session_factory
    
    await engine.dispose()

@pytest.fixture
async def user_repo(test_db):
    """테스트용 사용자 Repository"""
    async with test_db() as session:
        yield UserRepository(session)
```

### Repository 테스트

```python
@pytest.mark.asyncio
async def test_create_user(user_repo):
    """사용자 생성 테스트"""
    user_data = {
        "email": "test@example.com",
        "name": "Test User"
    }
    
    user = User(**user_data)
    created_user = await user_repo.create(user)
    
    assert created_user.id is not None
    assert created_user.email == user_data["email"]
    assert created_user.name == user_data["name"]

@pytest.mark.asyncio
async def test_get_user_by_email(user_repo):
    """이메일로 사용자 조회 테스트"""
    # 사용자 생성
    user = User(email="test@example.com", name="Test User")
    await user_repo.create(user)
    
    # 이메일로 조회
    found_user = await user_repo.get_by_email("test@example.com")
    
    assert found_user is not None
    assert found_user.email == "test@example.com"
```

## 모범 사례

1. **세션 관리**: 항상 컨텍스트 매니저 사용
2. **트랜잭션**: 관련된 여러 작업은 하나의 트랜잭션으로 묶기
3. **N+1 문제**: `selectinload`, `joinedload` 등을 사용하여 방지
4. **인덱스**: 자주 조회되는 컬럼에 인덱스 추가
5. **페이지네이션**: 대량 데이터 조회 시 페이지네이션 사용
6. **소프트 삭제**: 중요한 데이터는 소프트 삭제 사용
7. **연결 풀**: 적절한 연결 풀 크기 설정
8. **재시도**: 일시적인 연결 오류에 대한 재시도 로직 구현