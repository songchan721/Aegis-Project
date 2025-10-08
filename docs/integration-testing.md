# 통합 테스트 가이드

Aegis Shared Library를 다른 서비스와 통합하여 테스트하는 방법을 설명합니다.

## 개요

이 가이드는 다음과 같은 통합 테스트 시나리오를 다룹니다:

- User Service와의 통합
- Policy Service와의 통합
- 서비스 간 이벤트 통신 테스트
- 데이터베이스 스키마 통합 테스트
- 캐시 공유 테스트
- 모니터링 및 로깅 통합 테스트

## 1. User Service 통합 테스트

### 1.1 테스트 환경 설정

```python
# tests/integration/test_user_service_integration.py
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from aegis_shared.database import DatabaseManager
from aegis_shared.auth import JWTHandler
from aegis_shared.cache import CacheClient
from aegis_shared.messaging import EventPublisher, EventSubscriber
from aegis_shared.logging import configure_logging, get_logger

# User Service 모의 구현
class MockUserService:
    def __init__(self, shared_components):
        self.db_manager = shared_components['db_manager']
        self.cache = shared_components['cache']
        self.event_publisher = shared_components['event_publisher']
        self.jwt_handler = shared_components['jwt_handler']
        self.logger = get_logger(__name__)
    
    async def create_user(self, user_data):
        # Shared Library 사용
        async with self.db_manager.session() as session:
            # 사용자 생성 로직
            user_id = f"user-{user_data['email']}"
            
            # 캐시에 저장
            await self.cache.set(f"user:{user_id}", user_data, ttl=300)
            
            # 이벤트 발행
            await self.event_publisher.publish(
                topic="user-events",
                event_type="user.created",
                data={"user_id": user_id, **user_data}
            )
            
            self.logger.info("User created", user_id=user_id)
            return {"id": user_id, **user_data}

@pytest.fixture
async def shared_components():
    """공유 컴포넌트 설정"""
    # 데이터베이스
    db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
    
    # 캐시 (Mock)
    mock_redis = AsyncMock()
    cache = CacheClient(redis_client=mock_redis)
    
    # 이벤트 발행자 (Mock)
    mock_producer = AsyncMock()
    event_publisher = EventPublisher(kafka_producer=mock_producer)
    
    # JWT 핸들러
    jwt_handler = JWTHandler(secret_key="test-secret")
    
    components = {
        'db_manager': db_manager,
        'cache': cache,
        'event_publisher': event_publisher,
        'jwt_handler': jwt_handler
    }
    
    yield components
    
    await db_manager.close()

@pytest.mark.asyncio
async def test_user_service_integration(shared_components):
    """User Service 통합 테스트"""
    user_service = MockUserService(shared_components)
    
    # 사용자 생성 테스트
    user_data = {
        "email": "test@example.com",
        "name": "Test User"
    }
    
    user = await user_service.create_user(user_data)
    
    # 검증
    assert user["email"] == user_data["email"]
    assert user["name"] == user_data["name"]
    
    # 캐시 저장 확인
    shared_components['cache'].redis_client.set.assert_called()
    
    # 이벤트 발행 확인
    shared_components['event_publisher'].kafka_producer.send.assert_called()
```#
## 1.2 인증 통합 테스트

```python
@pytest.mark.asyncio
async def test_jwt_integration(shared_components):
    """JWT 인증 통합 테스트"""
    jwt_handler = shared_components['jwt_handler']
    
    # 토큰 생성
    user_data = {"user_id": "test-user", "email": "test@example.com"}
    token = jwt_handler.create_access_token(user_data)
    
    # 토큰 검증
    payload = jwt_handler.verify_token(token)
    
    assert payload["user_id"] == user_data["user_id"]
    assert payload["email"] == user_data["email"]

@pytest.mark.asyncio
async def test_auth_middleware_integration(shared_components):
    """인증 미들웨어 통합 테스트"""
    from aegis_shared.auth import AuthMiddleware
    from unittest.mock import Mock
    
    jwt_handler = shared_components['jwt_handler']
    middleware = AuthMiddleware(jwt_handler=jwt_handler)
    
    # 모의 요청 생성
    mock_request = Mock()
    token = jwt_handler.create_access_token({"user_id": "test-user"})
    mock_request.headers = {"Authorization": f"Bearer {token}"}
    mock_request.state = Mock()
    
    # 미들웨어 실행
    async def mock_call_next(request):
        return Mock()
    
    response = await middleware(mock_request, mock_call_next)
    
    # 사용자 정보가 설정되었는지 확인
    assert hasattr(mock_request.state, 'user')
    assert mock_request.state.user_id == "test-user"
```

## 2. Policy Service 통합 테스트

### 2.1 정책 서비스 모의 구현

```python
# tests/integration/test_policy_service_integration.py
class MockPolicyService:
    def __init__(self, shared_components):
        self.db_manager = shared_components['db_manager']
        self.cache = shared_components['cache']
        self.event_publisher = shared_components['event_publisher']
        self.logger = get_logger(__name__)
    
    async def create_policy(self, policy_data, user_id):
        """정책 생성"""
        async with self.db_manager.session() as session:
            policy_id = f"policy-{policy_data['title']}"
            
            # 정책 데이터 준비
            policy = {
                "id": policy_id,
                "created_by": user_id,
                **policy_data
            }
            
            # 캐시에 저장
            await self.cache.set(f"policy:{policy_id}", policy, ttl=600)
            
            # 이벤트 발행
            await self.event_publisher.publish(
                topic="policy-events",
                event_type="policy.created",
                data=policy,
                key=policy_id
            )
            
            self.logger.info("Policy created", policy_id=policy_id)
            return policy
    
    async def get_user_policies(self, user_id):
        """사용자 정책 조회 (캐시 활용)"""
        cache_key = f"user_policies:{user_id}"
        
        # 캐시에서 조회
        cached_policies = await self.cache.get(cache_key)
        if cached_policies:
            return cached_policies
        
        # 데이터베이스에서 조회 (모의)
        policies = [
            {"id": f"policy-{i}", "user_id": user_id, "title": f"Policy {i}"}
            for i in range(3)
        ]
        
        # 캐시에 저장
        await self.cache.set(cache_key, policies, ttl=300)
        
        return policies

@pytest.mark.asyncio
async def test_policy_service_integration(shared_components):
    """Policy Service 통합 테스트"""
    policy_service = MockPolicyService(shared_components)
    
    # 정책 생성 테스트
    policy_data = {
        "title": "Test Policy",
        "description": "Test policy description",
        "category": "business"
    }
    
    policy = await policy_service.create_policy(policy_data, "user-123")
    
    # 검증
    assert policy["title"] == policy_data["title"]
    assert policy["created_by"] == "user-123"
    
    # 캐시 및 이벤트 확인
    shared_components['cache'].redis_client.set.assert_called()
    shared_components['event_publisher'].kafka_producer.send.assert_called()

@pytest.mark.asyncio
async def test_policy_caching_integration(shared_components):
    """정책 캐싱 통합 테스트"""
    policy_service = MockPolicyService(shared_components)
    
    # 첫 번째 조회 (캐시 미스)
    shared_components['cache'].redis_client.get.return_value = None
    policies1 = await policy_service.get_user_policies("user-123")
    
    # 두 번째 조회 (캐시 히트)
    import json
    shared_components['cache'].redis_client.get.return_value = json.dumps(policies1).encode()
    policies2 = await policy_service.get_user_policies("user-123")
    
    # 결과 비교
    assert len(policies1) == 3
    assert policies1[0]["user_id"] == "user-123"
```

## 3. 서비스 간 이벤트 통신 테스트

### 3.1 이벤트 기반 통합 테스트

```python
# tests/integration/test_event_integration.py
@pytest.mark.asyncio
async def test_cross_service_events(shared_components):
    """서비스 간 이벤트 통신 테스트"""
    
    # 이벤트 구독자 설정
    mock_consumer = AsyncMock()
    event_subscriber = EventSubscriber(
        bootstrap_servers="localhost:9092",
        group_id="integration-test",
        topics=["user-events", "policy-events"]
    )
    event_subscriber._consumer = mock_consumer
    
    # 이벤트 핸들러 등록
    received_events = []
    
    @event_subscriber.handler("user.created")
    async def handle_user_created(event):
        received_events.append(("user.created", event))
    
    @event_subscriber.handler("policy.created")
    async def handle_policy_created(event):
        received_events.append(("policy.created", event))
    
    # User Service에서 이벤트 발행
    user_service = MockUserService(shared_components)
    await user_service.create_user({
        "email": "integration@example.com",
        "name": "Integration User"
    })
    
    # Policy Service에서 이벤트 발행
    policy_service = MockPolicyService(shared_components)
    await policy_service.create_policy({
        "title": "Integration Policy",
        "description": "Test policy"
    }, "user-123")
    
    # 이벤트 발행 확인
    event_publisher = shared_components['event_publisher']
    assert event_publisher.kafka_producer.send.call_count == 2
    
    # 발행된 이벤트 내용 확인
    calls = event_publisher.kafka_producer.send.call_args_list
    
    # 첫 번째 이벤트 (user.created)
    user_event = calls[0][0][1]  # 두 번째 인자가 이벤트 데이터
    assert user_event["event_type"] == "user.created"
    assert user_event["data"]["email"] == "integration@example.com"
    
    # 두 번째 이벤트 (policy.created)
    policy_event = calls[1][0][1]
    assert policy_event["event_type"] == "policy.created"
    assert policy_event["data"]["title"] == "Integration Policy"

@pytest.mark.asyncio
async def test_event_error_handling(shared_components):
    """이벤트 에러 처리 테스트"""
    
    # 실패하는 이벤트 핸들러
    @shared_components['event_subscriber'].handler("test.error")
    async def failing_handler(event):
        raise ValueError("Test error")
    
    # 에러 이벤트 처리 (실제로는 로그만 기록되고 계속 진행)
    mock_message = Mock()
    mock_message.value = json.dumps({
        "event_type": "test.error",
        "data": {"test": "data"}
    }).encode()
    
    # 에러가 발생해도 예외가 전파되지 않아야 함
    await shared_components['event_subscriber']._process_message(mock_message)
```

## 4. 데이터베이스 스키마 통합 테스트

### 4.1 스키마 레지스트리 통합

```python
# tests/integration/test_schema_integration.py
@pytest.mark.asyncio
async def test_schema_registry_integration():
    """스키마 레지스트리 통합 테스트"""
    from aegis_shared.schemas import SchemaRegistry
    from aegis_shared.migration import MigrationCoordinator
    import tempfile
    import os
    
    # 임시 스키마 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        schema_path = os.path.join(temp_dir, "schemas")
        os.makedirs(schema_path)
        
        # 테스트 스키마 파일 생성
        users_schema = """
name: users
owner: user-service
version: 1.0.0
columns:
  - name: id
    type: UUID
    primary_key: true
    nullable: false
  - name: email
    type: VARCHAR(255)
    unique: true
    nullable: false
references: []
"""
        
        policies_schema = """
name: policies
owner: policy-service
version: 1.0.0
columns:
  - name: id
    type: UUID
    primary_key: true
    nullable: false
  - name: user_id
    type: UUID
    nullable: false
  - name: title
    type: VARCHAR(200)
    nullable: false
references:
  - schema: users
    column: id
    foreign_key: user_id
    on_delete: CASCADE
"""
        
        # 스키마 파일 저장
        with open(os.path.join(schema_path, "users.yaml"), "w") as f:
            f.write(users_schema)
        
        with open(os.path.join(schema_path, "policies.yaml"), "w") as f:
            f.write(policies_schema)
        
        # 스키마 레지스트리 테스트
        registry = SchemaRegistry(registry_path=schema_path)
        
        # 스키마 로드 확인
        assert "users" in registry.schemas
        assert "policies" in registry.schemas
        
        # 의존성 분석
        dependent_services = registry.get_dependent_services("users")
        assert "policy-service" in dependent_services
        
        # 마이그레이션 순서 확인
        migration_order = registry.generate_migration_order()
        users_index = migration_order.index("users")
        policies_index = migration_order.index("policies")
        assert users_index < policies_index
        
        # 참조 무결성 검증
        errors = registry.validate_references()
        assert len(errors) == 0

@pytest.mark.asyncio
async def test_migration_coordination():
    """마이그레이션 조율 테스트"""
    from aegis_shared.schemas import SchemaRegistry
    from aegis_shared.migration import MigrationCoordinator
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 스키마 레지스트리 설정 (위와 동일)
        # ... (스키마 파일 생성 코드 생략)
        
        registry = SchemaRegistry(registry_path=temp_dir)
        coordinator = MigrationCoordinator(schema_registry=registry)
        
        # 마이그레이션 계획 수립
        schema_changes = {
            "users": "ALTER TABLE users ADD COLUMN phone VARCHAR(20);",
            "policies": "ALTER TABLE policies ADD COLUMN priority INTEGER DEFAULT 0;"
        }
        
        steps = coordinator.plan_migration(schema_changes)
        
        # 마이그레이션 단계 확인
        assert len(steps) == 2
        
        # 의존성 순서 확인
        users_step = next(s for s in steps if s.schema == "users")
        policies_step = next(s for s in steps if s.schema == "policies")
        
        assert users_step.service == "user-service"
        assert policies_step.service == "policy-service"
```

## 5. 캐시 공유 테스트

### 5.1 서비스 간 캐시 공유

```python
# tests/integration/test_cache_sharing.py
@pytest.mark.asyncio
async def test_cross_service_cache_sharing(shared_components):
    """서비스 간 캐시 공유 테스트"""
    
    user_service = MockUserService(shared_components)
    policy_service = MockPolicyService(shared_components)
    
    # User Service에서 사용자 정보 캐시
    user_data = {"id": "user-123", "email": "test@example.com", "name": "Test User"}
    await shared_components['cache'].set("user:user-123", user_data, ttl=300)
    
    # Policy Service에서 동일한 캐시 접근
    cached_user = await shared_components['cache'].get("user:user-123")
    
    # 캐시 공유 확인
    shared_components['cache'].redis_client.get.assert_called_with("user:user-123")

@pytest.mark.asyncio
async def test_cache_invalidation_across_services(shared_components):
    """서비스 간 캐시 무효화 테스트"""
    
    cache = shared_components['cache']
    
    # 여러 서비스에서 사용하는 캐시 키들
    cache_keys = [
        "user:user-123",
        "user_policies:user-123",
        "user_profile:user-123"
    ]
    
    # 캐시 데이터 설정
    for key in cache_keys:
        await cache.set(key, {"data": f"test-{key}"}, ttl=300)
    
    # 사용자 업데이트 시 관련 캐시 무효화
    for key in cache_keys:
        await cache.delete(key)
    
    # 무효화 확인
    for key in cache_keys:
        cache.redis_client.delete.assert_any_call(key)
```

## 6. 모니터링 및 로깅 통합 테스트

### 6.1 통합 모니터링 테스트

```python
# tests/integration/test_monitoring_integration.py
@pytest.mark.asyncio
async def test_cross_service_monitoring():
    """서비스 간 모니터링 통합 테스트"""
    from aegis_shared.monitoring import MetricsCollector
    from prometheus_client import CollectorRegistry
    
    # 공유 메트릭 레지스트리
    registry = CollectorRegistry()
    
    # 각 서비스의 메트릭 수집기
    user_metrics = MetricsCollector(registry=registry)
    policy_metrics = MetricsCollector(registry=registry)
    
    # User Service 메트릭
    user_metrics.increment_counter("users_created_total", {"service": "user-service"})
    user_metrics.observe_histogram("request_duration_seconds", 0.123, {"service": "user-service"})
    
    # Policy Service 메트릭
    policy_metrics.increment_counter("policies_created_total", {"service": "policy-service"})
    policy_metrics.observe_histogram("request_duration_seconds", 0.456, {"service": "policy-service"})
    
    # 통합 메트릭 출력
    metrics_output = user_metrics.get_metrics_output()
    
    # 두 서비스의 메트릭이 모두 포함되어 있는지 확인
    assert "users_created_total" in metrics_output
    assert "policies_created_total" in metrics_output
    assert "request_duration_seconds" in metrics_output

@pytest.mark.asyncio
async def test_distributed_logging():
    """분산 로깅 통합 테스트"""
    from aegis_shared.logging import configure_logging, get_logger, add_context
    import json
    from io import StringIO
    import sys
    
    # 로깅 설정
    configure_logging(service_name="integration-test", log_level="INFO")
    
    # 로그 출력 캡처
    log_capture = StringIO()
    
    # 각 서비스의 로거
    user_logger = get_logger("user-service")
    policy_logger = get_logger("policy-service")
    
    # 공통 컨텍스트 설정
    add_context(request_id="req-123", user_id="user-456")
    
    # 각 서비스에서 로그 생성
    user_logger.info("User operation completed", operation="create_user")
    policy_logger.info("Policy operation completed", operation="create_policy")
    
    # 로그 컨텍스트가 공유되는지 확인 (실제 구현에서는 로그 출력을 파싱해야 함)
    # 여기서는 컨텍스트 변수가 설정되었는지만 확인
    from aegis_shared.logging.context import request_id_var, user_id_var
    assert request_id_var.get() == "req-123"
    assert user_id_var.get() == "user-456"
```

## 7. 전체 통합 테스트 시나리오

### 7.1 엔드투엔드 통합 테스트

```python
# tests/integration/test_end_to_end.py
@pytest.mark.asyncio
async def test_complete_user_policy_workflow(shared_components):
    """완전한 사용자-정책 워크플로우 통합 테스트"""
    
    user_service = MockUserService(shared_components)
    policy_service = MockPolicyService(shared_components)
    
    # 1. 사용자 생성
    user_data = {
        "email": "workflow@example.com",
        "name": "Workflow User"
    }
    user = await user_service.create_user(user_data)
    user_id = user["id"]
    
    # 2. 정책 생성
    policy_data = {
        "title": "Workflow Policy",
        "description": "Test policy for workflow",
        "category": "business"
    }
    policy = await policy_service.create_policy(policy_data, user_id)
    
    # 3. 사용자 정책 조회 (캐시 활용)
    user_policies = await policy_service.get_user_policies(user_id)
    
    # 4. 검증
    assert user["email"] == user_data["email"]
    assert policy["created_by"] == user_id
    assert len(user_policies) > 0
    
    # 5. 이벤트 발행 확인
    event_publisher = shared_components['event_publisher']
    assert event_publisher.kafka_producer.send.call_count >= 2
    
    # 6. 캐시 사용 확인
    cache = shared_components['cache']
    cache.redis_client.set.assert_called()
    cache.redis_client.get.assert_called()

@pytest.mark.asyncio
async def test_error_propagation_across_services(shared_components):
    """서비스 간 에러 전파 테스트"""
    from aegis_shared.errors.exceptions import EntityNotFoundError
    
    policy_service = MockPolicyService(shared_components)
    
    # 존재하지 않는 사용자로 정책 생성 시도
    with pytest.raises(EntityNotFoundError):
        await policy_service.create_policy({
            "title": "Invalid Policy"
        }, "nonexistent-user")
```

## 8. 통합 테스트 실행

### 8.1 테스트 실행 스크립트

```bash
#!/bin/bash
# scripts/run_integration_tests.sh

echo "Starting Aegis Shared Library Integration Tests..."

# 테스트 환경 설정
export PYTHONPATH="${PYTHONPATH}:."
export TEST_ENV=integration

# 의존성 서비스 시작 (Docker Compose)
echo "Starting test dependencies..."
docker-compose -f docker-compose.test.yml up -d

# 서비스가 준비될 때까지 대기
echo "Waiting for services to be ready..."
sleep 10

# 통합 테스트 실행
echo "Running integration tests..."
pytest tests/integration/ -v --tb=short

# 테스트 결과 저장
TEST_RESULT=$?

# 정리
echo "Cleaning up test environment..."
docker-compose -f docker-compose.test.yml down

# 결과 반환
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All integration tests passed!"
else
    echo "❌ Some integration tests failed!"
fi

exit $TEST_RESULT
```

### 8.2 Docker Compose 테스트 환경

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: aegis_test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data

  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  kafka-test:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper-test:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9093:9092"
    depends_on:
      - zookeeper-test

  zookeeper-test:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
```

이제 Aegis Shared Library가 다른 서비스들과 원활하게 통합되는지 체계적으로 테스트할 수 있습니다!