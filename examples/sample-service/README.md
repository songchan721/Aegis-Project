# Sample Service

Aegis Shared Library를 사용하는 샘플 서비스입니다. 이 서비스는 shared library의 모든 주요 기능을 사용하는 예시를 제공합니다.

## 주요 기능

- **데이터베이스**: PostgreSQL + SQLAlchemy + Repository 패턴
- **인증**: JWT 토큰 기반 인증 및 권한 관리
- **로깅**: 구조화된 JSON 로깅
- **메시징**: Kafka 기반 이벤트 발행/구독
- **캐싱**: Redis 기반 캐싱
- **모니터링**: Prometheus 메트릭 수집
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
docker-compose logs -f sample-service
```

### 3. 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 및 Redis, Kafka 시작 (Docker Compose 사용)
docker-compose up -d postgres redis kafka

# 애플리케이션 실행
uvicorn main:app --reload
```

## API 사용 예시

### 1. 로그인 (JWT 토큰 획득)

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'
```

응답:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### 2. 사용자 생성

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "Test User"
  }'
```

### 3. 사용자 목록 조회

```bash
curl -X GET "http://localhost:8000/users/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 사용자 조회 (캐시됨)

```bash
curl -X GET "http://localhost:8000/users/USER_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. 사용자 업데이트

```bash
curl -X PUT "http://localhost:8000/users/USER_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name"
  }'
```

### 6. 사용자 분석 데이터

```bash
curl -X GET "http://localhost:8000/users/USER_ID/analytics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 모니터링

### Prometheus 메트릭

- **URL**: http://localhost:9090
- **메트릭 엔드포인트**: http://localhost:8000/metrics

### Grafana 대시보드

- **URL**: http://localhost:3000
- **로그인**: admin / admin

## 로그 확인

### 구조화된 로그 예시

```json
{
  "event": "User created successfully",
  "level": "info",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "service": "sample-service",
  "request_id": "req-123",
  "user_id": "user-456",
  "user_id": "user-789"
}
```

### Docker Compose 로그

```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f sample-service
```

## 이벤트 메시징

### 발행되는 이벤트

1. **user.created**: 사용자 생성 시
2. **user.updated**: 사용자 업데이트 시
3. **user.deleted**: 사용자 삭제 시

### Kafka 토픽 확인

```bash
# Kafka 컨테이너 접속
docker-compose exec kafka bash

# 토픽 목록 확인
kafka-topics --bootstrap-server localhost:9092 --list

# 이벤트 확인
kafka-console-consumer --bootstrap-server localhost:9092 --topic user-events --from-beginning
```

## 캐싱

### Redis 캐시 확인

```bash
# Redis 컨테이너 접속
docker-compose exec redis redis-cli

# 캐시된 키 확인
KEYS *

# 특정 키 값 확인
GET user:USER_ID
```

## 테스트

### 단위 테스트

```bash
# 테스트 실행
pytest tests/

# 커버리지와 함께
pytest --cov=. tests/
```

### 통합 테스트

```bash
# 통합 테스트 실행
pytest tests/integration/
```

## 개발 팁

### 1. 로깅 컨텍스트 사용

```python
from aegis_shared.logging import add_context, get_logger

logger = get_logger(__name__)

# 컨텍스트 설정
add_context(request_id="req-123", user_id="user-456")

# 로그 기록 (컨텍스트 자동 포함)
logger.info("Operation completed", operation="create_user")
```

### 2. 메트릭 수집

```python
from aegis_shared.monitoring import MetricsCollector

metrics = MetricsCollector()

# 데코레이터 사용
@metrics.track_requests()
async def my_endpoint():
    pass

# 수동 메트릭
metrics.increment_counter("custom_counter", labels={"type": "test"})
```

### 3. 캐싱 사용

```python
from aegis_shared.cache import CacheClient

# 데코레이터 사용
@cache.cached(ttl=300)
async def expensive_operation():
    pass

# 수동 캐시
await cache.set("key", "value", ttl=300)
value = await cache.get("key")
```

## 문제 해결

### 일반적인 문제

1. **데이터베이스 연결 실패**
   - DATABASE_URL 환경 변수 확인
   - PostgreSQL 서비스 상태 확인

2. **Redis 연결 실패**
   - REDIS_URL 환경 변수 확인
   - Redis 서비스 상태 확인

3. **Kafka 연결 실패**
   - KAFKA_BOOTSTRAP_SERVERS 환경 변수 확인
   - Kafka 서비스 상태 확인

### 로그 레벨 조정

```bash
# 환경 변수로 설정
export LOG_LEVEL=DEBUG

# 또는 .env 파일에서
LOG_LEVEL=DEBUG
```

## 라이선스

MIT License