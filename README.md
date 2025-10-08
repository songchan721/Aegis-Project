# Aegis Shared Library

이지스(Aegis) 시스템의 모든 마이크로서비스가 공통으로 사용하는 핵심 기능을 제공하는 중앙 집중식 라이브러리입니다.

## 🚀 주요 기능

- **데이터베이스 연결 및 Repository 패턴**: 일관된 데이터베이스 접근 및 CRUD 작업
- **인증 및 인가**: JWT 토큰 처리, 미들웨어, RBAC 시스템
- **구조화된 로깅**: JSON 형식의 중앙 집중식 로깅 시스템
- **이벤트 메시징**: Kafka 기반 이벤트 발행 및 구독
- **모니터링 및 메트릭**: Prometheus 메트릭 수집 및 분산 추적
- **캐싱**: Redis 기반 캐싱 시스템
- **설정 관리**: 환경별 설정 및 시크릿 관리
- **에러 처리**: 표준화된 예외 처리 및 에러 코드
- **스키마 레지스트리**: 중앙 집중식 데이터베이스 스키마 관리
- **마이그레이션 조율**: 서비스 간 데이터베이스 마이그레이션 조율

## 📦 설치

### Poetry를 사용하는 경우 (권장)

```bash
# 의존성 설치
poetry install

# 또는 프로덕션 의존성만 설치
poetry install --only main
```

### pip를 사용하는 경우

```bash
# 프로덕션 의존성 설치
pip install -r requirements.txt

# 개발 의존성 포함 설치
pip install -r requirements-dev.txt
```

### 패키지로 설치

```bash
# Poetry를 사용하는 경우
poetry add aegis-shared

# pip를 사용하는 경우
pip install aegis-shared
```

### ⚠️ 플랫폼별 주의사항

**Windows 사용자**:
- `python-magic-bin` 패키지가 자동으로 설치됩니다 (Windows용 libmagic 포함)
- Poetry 사용시: `poetry install`로 자동 설치됨
- Pip 사용시: `requirements-dev.txt`에 포함됨

**Linux/macOS 사용자**:
- libmagic이 시스템에 설치되어 있어야 합니다
- Ubuntu/Debian: `sudo apt-get install libmagic1`
- macOS: `brew install libmagic`
- 또는 `python-magic-bin` 사용 가능

**중요**: 
- Pydantic v2를 사용하므로 `pydantic-settings` 패키지가 필요합니다
- Redis 캐싱 테스트를 위해 `fakeredis` 패키지가 필요합니다
- Poetry를 사용하는 경우 `poetry install` 또는 `poetry update`를 실행하여 모든 의존성을 설치하세요

## 🏗️ 아키텍처

```
aegis-shared/
├── aegis_shared/
│   ├── auth/           # 인증 및 인가
│   ├── cache/          # 캐싱 시스템
│   ├── config/         # 설정 관리
│   ├── database/       # 데이터베이스 연결 및 Repository
│   ├── errors/         # 에러 처리
│   ├── logging/        # 구조화된 로깅
│   ├── messaging/      # 이벤트 메시징
│   ├── migration/      # 마이그레이션 조율
│   ├── models/         # 공통 데이터 모델
│   ├── monitoring/     # 모니터링 및 메트릭
│   ├── schemas/        # 스키마 레지스트리
│   └── utils/          # 유틸리티 함수
└── tests/              # 테스트 코드
```

## 🚀 빠른 시작

### 1. 기본 설정

```python
from aegis_shared.config import Settings
from aegis_shared.logging import configure_logging

# 설정 로드
settings = Settings()

# 로깅 설정
configure_logging(
    service_name="my-service",
    log_level=settings.log_level
)
```

### 2. 데이터베이스 사용

```python
from aegis_shared.database import DatabaseManager, BaseRepository
from aegis_shared.models import BaseEntity

# 데이터베이스 매니저 초기화
db_manager = DatabaseManager(database_url=settings.database_url)

# Repository 사용
class User(BaseEntity):
    email: str
    name: str

class UserRepository(BaseRepository[User]):
    pass

# 사용 예시
async with db_manager.session() as session:
    user_repo = UserRepository(session, User)
    user = await user_repo.get_by_id("user-123")
```

### 3. 인증 시스템

```python
from aegis_shared.auth import JWTHandler, AuthMiddleware

# JWT 핸들러 초기화
jwt_handler = JWTHandler(secret_key=settings.jwt_secret)

# 토큰 생성
token = jwt_handler.create_access_token({
    "user_id": "user-123",
    "email": "user@example.com"
})

# 토큰 검증
payload = jwt_handler.verify_token(token)
```

### 4. 이벤트 메시징

```python
from aegis_shared.messaging import EventPublisher, EventSubscriber

# 이벤트 발행
publisher = EventPublisher(kafka_producer=kafka_producer)
await publisher.publish(
    topic="user-events",
    event_type="user.created",
    data={"user_id": "user-123", "email": "user@example.com"}
)

# 이벤트 구독
subscriber = EventSubscriber(
    bootstrap_servers="localhost:9092",
    group_id="my-service",
    topics=["user-events"]
)

@subscriber.handler("user.created")
def handle_user_created(event):
    print(f"User created: {event['data']['user_id']}")
```

### 5. 캐싱

```python
from aegis_shared.cache import CacheClient

cache = CacheClient(redis_client=redis_client)

# 캐시 데코레이터 사용
@cache.cached(ttl=300)
async def get_user_data(user_id: str):
    # 비용이 많이 드는 작업
    return await fetch_user_from_database(user_id)
```

### 6. 모니터링

```python
from aegis_shared.monitoring import MetricsCollector

metrics = MetricsCollector()

# 메트릭 데코레이터 사용
@metrics.track_requests()
@metrics.track_database_queries()
async def get_user_policies(user_id: str):
    # 비즈니스 로직
    return policies
```

## 📚 상세 문서

- [인증 및 인가](docs/auth.md)
- [데이터베이스](docs/database.md)
- [로깅](docs/logging.md)
- [메시징](docs/messaging.md)
- [모니터링](docs/monitoring.md)
- [캐싱](docs/caching.md)
- [설정 관리](docs/config.md)
- [스키마 레지스트리](docs/schema-registry.md)
- [마이그레이션 조율](docs/migration.md)

## 🧪 테스트

```bash
# 모든 테스트 실행
poetry run pytest

# 커버리지와 함께 테스트 실행
poetry run pytest --cov=aegis_shared --cov-report=html

# 특정 모듈 테스트
poetry run pytest aegis_shared/tests/test_auth.py
```

## 🔧 개발

### 개발 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd aegis-shared

# 의존성 설치
poetry install

# 개발 도구 설치
poetry install --group dev
```

### 코드 품질

```bash
# 린팅
poetry run flake8 aegis_shared/

# 타입 체크
poetry run mypy aegis_shared/

# 포맷팅
poetry run black aegis_shared/
```

## 📋 요구사항

- Python 3.11+
- PostgreSQL (데이터베이스)
- Redis (캐싱)
- Apache Kafka (메시징)

## 🤝 기여

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

문제가 발생하거나 질문이 있으시면:

1. [Issues](../../issues)에서 기존 이슈를 확인하세요
2. 새로운 이슈를 생성하세요
3. 문서를 확인하세요

## 🔄 변경 로그

변경 사항은 [CHANGELOG.md](CHANGELOG.md)에서 확인할 수 있습니다.