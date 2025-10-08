# 사용자 서비스 테스트 전략

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-SPC-USER-20250917-8.0 |
| 버전 | 8.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 사용자 서비스에 대한 포괄적인 테스트 전략을 정의한다. **테스트 피라미드** 원칙을 따라 단위 테스트부터 E2E 테스트까지 체계적인 테스트 접근법을 제시한다.

## 2. 테스트 전략 개요

### 2.1. 테스트 피라미드

```mermaid
graph TB
    subgraph "테스트 피라미드"
        A[E2E Tests<br/>10%]
        B[Integration Tests<br/>20%]
        C[Unit Tests<br/>70%]
    end
    
    subgraph "테스트 유형별 특성"
        D[느림, 비싸지만 높은 신뢰도]
        E[중간 속도, 중간 비용]
        F[빠름, 저렴하지만 낮은 신뢰도]
    end
    
    A --> D
    B --> E
    C --> F
```

### 2.2. 테스트 목표
- **품질 보증**: 코드 품질과 기능 정확성 보장
- **회귀 방지**: 새로운 변경사항이 기존 기능에 미치는 영향 최소화
- **문서화**: 테스트 코드를 통한 기능 명세 문서화
- **신뢰성**: 배포 전 충분한 검증을 통한 서비스 안정성 확보

## 3. 단위 테스트 (Unit Tests)

### 3.1. 테스트 범위
- 도메인 모델 메서드
- 비즈니스 로직 함수
- 유틸리티 함수
- 검증 로직

### 3.2. 단위 테스트 예시

#### 사용자 도메인 모델 테스트
```python
import pytest
from datetime import datetime, timedelta
from src.domain.models.user import User, UserStatus
from src.domain.value_objects.email import Email

class TestUser:
    """사용자 도메인 모델 테스트"""
    
    def test_user_creation(self):
        """사용자 생성 테스트"""
        # Given
        user_id = "test-user-id"
        email = "test@example.com"
        password_hash = "hashed_password"
        
        # When
        user = User(
            user_id=user_id,
            email=email,
            password_hash=password_hash
        )
        
        # Then
        assert user.user_id == user_id
        assert user.email == email
        assert user.status == UserStatus.PENDING_VERIFICATION
        assert not user.email_verified
        assert user.login_count == 0
    
    def test_email_verification(self):
        """이메일 인증 테스트"""
        # Given
        user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password"
        )
        
        # When
        user.verify_email()
        
        # Then
        assert user.email_verified
        assert user.status == UserStatus.ACTIVE
    
    def test_successful_login_record(self):
        """성공적인 로그인 기록 테스트"""
        # Given
        user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password",
            status=UserStatus.ACTIVE,
            failed_login_attempts=3
        )
        
        # When
        user.record_successful_login()
        
        # Then
        assert user.login_count == 1
        assert user.failed_login_attempts == 0
        assert user.last_login_at is not None
        assert user.locked_until is None
    
    def test_failed_login_attempts(self):
        """실패한 로그인 시도 테스트"""
        # Given
        user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password",
            status=UserStatus.ACTIVE
        )
        
        # When - 5번 실패
        for _ in range(5):
            user.record_failed_login()
        
        # Then
        assert user.failed_login_attempts == 5
        assert user.is_locked()
        assert not user.can_login()
    
    def test_account_unlock_after_timeout(self):
        """시간 경과 후 계정 잠금 해제 테스트"""
        # Given
        user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password",
            status=UserStatus.ACTIVE,
            locked_until=datetime.utcnow() - timedelta(minutes=1)  # 1분 전에 잠금
        )
        
        # When & Then
        assert not user.is_locked()
        assert user.can_login()
```

#### 비즈니스 로직 테스트
```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.application.services.user_service import UserService
from src.domain.models.user import User
from src.domain.exceptions import UserAlreadyExistsError

class TestUserService:
    """사용자 서비스 테스트"""
    
    @pytest.fixture
    def user_service(self):
        """사용자 서비스 픽스처"""
        user_repository = Mock()
        profile_repository = Mock()
        auth_service = Mock()
        event_publisher = Mock()
        
        return UserService(
            user_repository=user_repository,
            profile_repository=profile_repository,
            auth_service=auth_service,
            event_publisher=event_publisher
        )
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service):
        """사용자 등록 성공 테스트"""
        # Given
        registration_data = Mock()
        registration_data.email = "test@example.com"
        registration_data.password = "password123"
        registration_data.business_registration_number = "123-45-67890"
        
        user_service.user_repository.find_by_email = AsyncMock(return_value=None)
        user_service.verify_business_registration = AsyncMock(return_value=Mock())
        user_service.auth_service.hash_password = AsyncMock(return_value="hashed_password")
        user_service.user_repository.save = AsyncMock()
        user_service.profile_repository.save = AsyncMock()
        user_service.event_publisher.publish = AsyncMock()
        user_service.send_verification_email = AsyncMock()
        
        # When
        result = await user_service.register_user(registration_data)
        
        # Then
        assert result.status == "pending_verification"
        user_service.user_repository.save.assert_called_once()
        user_service.profile_repository.save.assert_called_once()
        user_service.event_publisher.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, user_service):
        """중복 이메일 등록 테스트"""
        # Given
        registration_data = Mock()
        registration_data.email = "test@example.com"
        
        existing_user = Mock()
        user_service.user_repository.find_by_email = AsyncMock(return_value=existing_user)
        
        # When & Then
        with pytest.raises(UserAlreadyExistsError):
            await user_service.register_user(registration_data)
```

### 3.3. 단위 테스트 실행 설정

#### pytest 설정 (pytest.ini)
```ini
[tool:pytest]
testpaths = tests/unit
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

## 4. 통합 테스트 (Integration Tests)

### 4.1. 테스트 범위
- 데이터베이스 연동
- 외부 API 호출
- 메시지 큐 연동
- 캐시 시스템 연동

### 4.2. 통합 테스트 예시

#### 데이터베이스 통합 테스트
```python
import pytest
import asyncpg
from testcontainers.postgres import PostgresContainer
from src.infrastructure.repositories.postgresql_user_repository import PostgreSQLUserRepository
from src.domain.models.user import User, UserStatus

class TestPostgreSQLUserRepository:
    """PostgreSQL 사용자 리포지토리 통합 테스트"""
    
    @pytest.fixture(scope="class")
    async def postgres_container(self):
        """PostgreSQL 테스트 컨테이너"""
        with PostgresContainer("postgres:15") as postgres:
            yield postgres
    
    @pytest.fixture
    async def db_connection(self, postgres_container):
        """데이터베이스 연결"""
        connection_string = postgres_container.get_connection_url()
        connection = await asyncpg.connect(connection_string)
        
        # 테이블 생성
        await self._create_tables(connection)
        
        yield connection
        
        await connection.close()
    
    @pytest.fixture
    async def user_repository(self, db_connection):
        """사용자 리포지토리"""
        return PostgreSQLUserRepository(db_connection)
    
    async def _create_tables(self, connection):
        """테스트용 테이블 생성"""
        await connection.execute("""
            CREATE TABLE users (
                user_id UUID PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending_verification',
                email_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                last_login_at TIMESTAMPTZ,
                login_count INTEGER DEFAULT 0,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMPTZ
            )
        """)
    
    @pytest.mark.integration
    async def test_save_and_find_user(self, user_repository):
        """사용자 저장 및 조회 테스트"""
        # Given
        user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password"
        )
        
        # When
        await user_repository.save(user)
        found_user = await user_repository.find_by_id("test-user-id")
        
        # Then
        assert found_user is not None
        assert found_user.user_id == user.user_id
        assert found_user.email == user.email
        assert found_user.status == UserStatus.PENDING_VERIFICATION
    
    @pytest.mark.integration
    async def test_find_by_email(self, user_repository):
        """이메일로 사용자 조회 테스트"""
        # Given
        user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await user_repository.save(user)
        
        # When
        found_user = await user_repository.find_by_email("test@example.com")
        
        # Then
        assert found_user is not None
        assert found_user.email == "test@example.com"
    
    @pytest.mark.integration
    async def test_user_not_found(self, user_repository):
        """존재하지 않는 사용자 조회 테스트"""
        # When
        found_user = await user_repository.find_by_id("non-existent-id")
        
        # Then
        assert found_user is None
```

#### API 통합 테스트
```python
import pytest
from httpx import AsyncClient
from src.main import app

class TestUserAPI:
    """사용자 API 통합 테스트"""
    
    @pytest.fixture
    async def client(self):
        """테스트 클라이언트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.integration
    async def test_user_registration_success(self, client):
        """사용자 등록 성공 테스트"""
        # Given
        registration_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "business_registration_number": "123-45-67890",
            "terms_agreed": True,
            "privacy_policy_agreed": True
        }
        
        # When
        response = await client.post("/api/v1/users/auth/register", json=registration_data)
        
        # Then
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending_verification"
        assert "user_id" in data["data"]
    
    @pytest.mark.integration
    async def test_user_registration_duplicate_email(self, client):
        """중복 이메일 등록 테스트"""
        # Given
        registration_data = {
            "email": "duplicate@example.com",
            "password": "SecurePassword123!",
            "business_registration_number": "123-45-67890",
            "terms_agreed": True,
            "privacy_policy_agreed": True
        }
        
        # 첫 번째 등록
        await client.post("/api/v1/users/auth/register", json=registration_data)
        
        # When - 두 번째 등록 시도
        response = await client.post("/api/v1/users/auth/register", json=registration_data)
        
        # Then
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"
```

## 5. E2E 테스트 (End-to-End Tests)

### 5.1. 테스트 범위
- 전체 사용자 여정
- 크로스 서비스 시나리오
- 실제 환경과 유사한 조건

### 5.2. E2E 테스트 예시

#### 사용자 등록부터 로그인까지 전체 플로우
```python
import pytest
from playwright.async_api import async_playwright

class TestUserJourney:
    """사용자 여정 E2E 테스트"""
    
    @pytest.mark.e2e
    async def test_complete_user_registration_flow(self):
        """완전한 사용자 등록 플로우 테스트"""
        async with async_playwright() as p:
            # Given
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                # When - 회원가입 페이지 접속
                await page.goto("http://localhost:3000/register")
                
                # 회원가입 폼 작성
                await page.fill('[data-testid="email-input"]', "e2e@example.com")
                await page.fill('[data-testid="password-input"]', "SecurePassword123!")
                await page.fill('[data-testid="business-reg-input"]', "123-45-67890")
                await page.check('[data-testid="terms-checkbox"]')
                await page.check('[data-testid="privacy-checkbox"]')
                
                # 회원가입 버튼 클릭
                await page.click('[data-testid="register-button"]')
                
                # Then - 성공 메시지 확인
                success_message = await page.wait_for_selector('[data-testid="success-message"]')
                assert "회원가입이 완료되었습니다" in await success_message.text_content()
                
                # 이메일 인증 시뮬레이션 (테스트 환경에서는 자동 인증)
                await self._simulate_email_verification("e2e@example.com")
                
                # 로그인 페이지로 이동
                await page.goto("http://localhost:3000/login")
                
                # 로그인 폼 작성
                await page.fill('[data-testid="login-email"]', "e2e@example.com")
                await page.fill('[data-testid="login-password"]', "SecurePassword123!")
                await page.click('[data-testid="login-button"]')
                
                # 대시보드 페이지로 리다이렉트 확인
                await page.wait_for_url("**/dashboard")
                
                # 사용자 정보 표시 확인
                user_info = await page.wait_for_selector('[data-testid="user-info"]')
                assert "e2e@example.com" in await user_info.text_content()
                
            finally:
                await browser.close()
    
    async def _simulate_email_verification(self, email: str):
        """이메일 인증 시뮬레이션"""
        # 테스트 환경에서는 API를 직접 호출하여 인증 처리
        async with AsyncClient(base_url="http://localhost:8000") as client:
            # 테스트용 인증 토큰 생성 및 인증 처리
            response = await client.post(
                "/api/v1/users/auth/test-verify-email",
                json={"email": email}
            )
            assert response.status_code == 200
```

## 6. 성능 테스트 (Performance Tests)

### 6.1. 부하 테스트

#### Locust를 사용한 부하 테스트
```python
from locust import HttpUser, task, between

class UserServiceLoadTest(HttpUser):
    """사용자 서비스 부하 테스트"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """테스트 시작 시 실행"""
        self.login()
    
    def login(self):
        """로그인"""
        response = self.client.post("/api/v1/users/auth/login", json={
            "email": "loadtest@example.com",
            "password": "LoadTestPassword123!"
        })
        
        if response.status_code == 200:
            token = response.json()["data"]["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    @task(3)
    def get_profile(self):
        """프로필 조회 (가중치 3)"""
        self.client.get("/api/v1/users/profile")
    
    @task(1)
    def update_profile(self):
        """프로필 업데이트 (가중치 1)"""
        self.client.put("/api/v1/users/profile", json={
            "business_profile": {
                "annual_revenue": 100000000,
                "employee_count": 5
            }
        })
    
    @task(2)
    def get_preferences(self):
        """선호도 조회 (가중치 2)"""
        self.client.get("/api/v1/users/settings/notifications")
```

## 7. 테스트 데이터 관리

### 7.1. 테스트 픽스처

```python
import pytest
from datetime import datetime
from src.domain.models.user import User, UserStatus

@pytest.fixture
def sample_user():
    """샘플 사용자 픽스처"""
    return User(
        user_id="sample-user-id",
        email="sample@example.com",
        password_hash="hashed_password",
        status=UserStatus.ACTIVE,
        email_verified=True,
        created_at=datetime(2025, 1, 1, 10, 0, 0)
    )

@pytest.fixture
def sample_users():
    """여러 샘플 사용자 픽스처"""
    return [
        User(
            user_id=f"user-{i}",
            email=f"user{i}@example.com",
            password_hash="hashed_password",
            status=UserStatus.ACTIVE
        )
        for i in range(1, 6)
    ]

@pytest.fixture
async def clean_database():
    """데이터베이스 정리 픽스처"""
    # 테스트 전 데이터베이스 정리
    yield
    # 테스트 후 데이터베이스 정리
    await cleanup_test_data()
```

### 7.2. 팩토리 패턴

```python
import factory
from datetime import datetime
from src.domain.models.user import User, UserStatus

class UserFactory(factory.Factory):
    """사용자 팩토리"""
    
    class Meta:
        model = User
    
    user_id = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password_hash = "hashed_password"
    status = UserStatus.ACTIVE
    email_verified = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    login_count = 0
    failed_login_attempts = 0

# 사용 예시
def test_user_creation():
    user = UserFactory()
    assert user.email.endswith("@example.com")
    assert user.status == UserStatus.ACTIVE
```

## 8. 테스트 자동화

### 8.1. CI/CD 파이프라인 통합

#### GitHub Actions 워크플로우
```yaml
name: User Service Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: |
          pytest tests/unit --cov=src --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run integration tests
        run: |
          pytest tests/integration -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
          playwright install
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.test.yml up -d
          sleep 30
      
      - name: Run E2E tests
        run: |
          pytest tests/e2e -v
      
      - name: Stop services
        run: |
          docker-compose -f docker-compose.test.yml down
```

## 9. 테스트 메트릭 및 리포팅

### 9.1. 커버리지 목표
- **단위 테스트 커버리지**: 80% 이상
- **통합 테스트 커버리지**: 60% 이상
- **전체 커버리지**: 75% 이상

### 9.2. 품질 게이트
- 모든 테스트 통과 필수
- 커버리지 목표 달성 필수
- 성능 테스트 기준 충족 필수
- 보안 테스트 통과 필수

---

**📋 관련 문서**
- [기술 설계](./03_TECHNICAL_DESIGN.md)
- [API 명세](./04_API_SPECIFICATION.md)
- [데이터 모델](./05_DATA_MODEL.md)
- [테스트 전략](../../../06_QUALITY_ASSURANCE/01_TESTING_STRATEGY.md)