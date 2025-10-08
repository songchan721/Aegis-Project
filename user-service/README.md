# User Service

Aegis Shared Library를 사용하는 사용자 인증 및 관리 서비스입니다.

## 주요 기능

- **사용자 등록 및 인증**: 이메일 기반 사용자 등록 및 JWT 토큰 인증
- **이메일 인증**: 이메일 주소 검증 시스템
- **비밀번호 관리**: 안전한 비밀번호 해싱 및 재설정 기능
- **세션 관리**: Redis 기반 세션 및 토큰 관리
- **보안 기능**: 계정 잠금, 로그인 시도 제한, 의심스러운 활동 감지
- **로깅 및 모니터링**: 구조화된 로깅 및 Prometheus 메트릭

## Shared Library 통합

이 서비스는 Aegis Shared Library의 다음 기능들을 사용합니다:

- **데이터베이스**: PostgreSQL 연결 및 Repository 패턴
- **인증**: JWT 토큰 생성 및 검증
- **캐싱**: Redis 기반 캐싱
- **메시징**: Kafka 이벤트 발행
- **로깅**: 구조화된 JSON 로깅
- **모니터링**: Prometheus 메트릭 수집
- **설정 관리**: 환경별 설정 관리
- **에러 처리**: 표준화된 예외 처리

## 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 파일 복사
cp .env.example .env

# 필요에 따라 .env 파일 수정
```

### 2. Docker Compose로 실행

```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f user-service
```

### 3. 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 및 Redis, Kafka 시작
docker-compose up -d postgres redis kafka

# 애플리케이션 실행
uvicorn app.main:app --reload --port 8001
```

## API 엔드포인트

### 기본 엔드포인트

- `GET /` - 서비스 정보
- `GET /health` - 헬스 체크
- `GET /metrics` - Prometheus 메트릭

### 인증 API (예정)

- `POST /auth/register` - 사용자 등록
- `POST /auth/login` - 로그인
- `POST /auth/logout` - 로그아웃
- `POST /auth/refresh` - 토큰 갱신
- `POST /auth/verify-email` - 이메일 인증
- `POST /auth/forgot-password` - 비밀번호 재설정 요청
- `POST /auth/reset-password` - 비밀번호 재설정

### 사용자 API (예정)

- `GET /users/profile` - 프로필 조회
- `PUT /users/profile` - 프로필 수정
- `POST /users/change-email` - 이메일 변경
- `DELETE /users/account` - 계정 삭제

### 세션 API (예정)

- `GET /sessions` - 활성 세션 목록
- `DELETE /sessions/{session_id}` - 특정 세션 종료
- `DELETE /sessions/all` - 모든 세션 종료

## 데이터베이스 스키마

### Users 테이블

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP NULL,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);
```

### Login History 테이블

```sql
CREATE TABLE login_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 환경 변수

주요 환경 변수들:

```bash
# 애플리케이션
APP_ENV=development
DEBUG=true
PORT=8001

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:password@localhost/user_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# JWT
JWT_SECRET=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 이메일
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-password

# 보안
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
```

## 테스트

### 통합 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/

# 특정 테스트 파일 실행
pytest tests/test_integration.py -v

# 커버리지와 함께 실행
pytest --cov=app tests/
```

### Shared Library 통합 확인

```bash
# 통합 테스트로 shared library 기능 확인
pytest tests/test_integration.py::TestSharedLibraryIntegration -v
```

## 모니터링

### Prometheus 메트릭

- **URL**: http://localhost:9091 (Prometheus)
- **메트릭 엔드포인트**: http://localhost:8001/metrics

### 로그 확인

```bash
# Docker Compose 로그
docker-compose logs -f user-service

# 구조화된 로그 예시
{
  "event": "User login successful",
  "level": "info",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "service": "user-service",
  "user_id": "user-123",
  "request_id": "req-456"
}
```

## 개발 가이드

### Shared Library 사용 패턴

#### 1. 데이터베이스 Repository

```python
from aegis_shared.database import BaseRepository

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> Optional[User]:
        # 커스텀 쿼리 구현
        pass
```

#### 2. JWT 인증

```python
from aegis_shared.auth import JWTHandler

jwt_handler = JWTHandler(secret_key=settings.jwt_secret)
token = jwt_handler.create_access_token({"user_id": user.id})
```

#### 3. 이벤트 발행

```python
from aegis_shared.messaging import EventPublisher

await event_publisher.publish(
    topic="user-events",
    event_type="user.registered",
    data={"user_id": user.id, "email": user.email}
)
```

#### 4. 캐싱

```python
from aegis_shared.cache import CacheClient

@cache_client.cached(ttl=300)
async def get_user_profile(user_id: str):
    # 캐시된 함수
    pass
```

#### 5. 로깅

```python
from aegis_shared.logging import get_logger, add_context

logger = get_logger(__name__)
add_context(user_id=user.id)
logger.info("User action completed", action="login")
```

## 보안 고려사항

- 비밀번호는 bcrypt로 해싱
- JWT 토큰은 짧은 만료 시간 설정
- 로그인 실패 시 계정 잠금
- 의심스러운 로그인 패턴 감지
- 모든 민감한 작업에 대한 로깅
- CORS 및 보안 헤더 설정

## 라이선스

MIT License