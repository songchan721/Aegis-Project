# 이지스(Aegis) 이벤트 스키마 명세서

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-API-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 이벤트 기반 아키텍처에서 사용되는 모든 이벤트 스키마를 정의한다. **Apache Kafka**를 통해 전송되는 이벤트들의 구조, 버전 관리, 호환성 규칙을 명시하여 시스템 간 안정적인 비동기 통신을 보장한다.

## 2. 이벤트 아키텍처 원칙

### 2.1. 핵심 원칙
- **스키마 진화**: 하위 호환성을 보장하는 스키마 변경
- **이벤트 불변성**: 발행된 이벤트는 변경되지 않음
- **순서 보장**: 동일 파티션 내 이벤트 순서 보장
- **최소 한 번 전달**: At-least-once 전달 보장

### 2.2. 이벤트 분류

#### 도메인 이벤트 (Domain Events)
- **정책 이벤트**: 정책 데이터 변경 관련
- **사용자 이벤트**: 사용자 활동 및 프로필 변경
- **추천 이벤트**: 추천 생성 및 피드백 관련

#### 시스템 이벤트 (System Events)
- **데이터 동기화**: CDC 이벤트
- **시스템 상태**: 헬스체크, 메트릭
- **보안 이벤트**: 인증, 인가, 보안 위협

## 3. Kafka 토픽 구조

### 3.1. 토픽 네이밍 컨벤션
```
{environment}.{domain}.{entity}.{version}

예시:
- prod.aegis.policy.v1
- prod.aegis.user.v1
- prod.aegis.recommendation.v1
- prod.aegis.system.v1
```

### 3.2. 토픽 목록 및 설정

| 토픽명 | 파티션 수 | 복제 인수 | 보존 기간 | 설명 |
|--------|-----------|-----------|-----------|------|
| `aegis.policy.v1` | 6 | 3 | 30일 | 정책 데이터 변경 이벤트 |
| `aegis.user.v1` | 3 | 3 | 7일 | 사용자 활동 이벤트 |
| `aegis.recommendation.v1` | 6 | 3 | 7일 | 추천 생성 및 피드백 |
| `aegis.system.v1` | 3 | 3 | 3일 | 시스템 상태 이벤트 |
| `aegis.security.v1` | 3 | 3 | 90일 | 보안 관련 이벤트 |

## 4. 공통 이벤트 구조

### 4.1. 기본 이벤트 엔벨로프
모든 이벤트는 다음 공통 구조를 따른다:

```json
{
  "eventId": "uuid-v4",
  "eventType": "PolicyCreated",
  "eventVersion": "1.0",
  "source": "policy-service",
  "timestamp": "2025-09-17T10:30:00.000Z",
  "correlationId": "request-uuid",
  "causationId": "parent-event-uuid",
  "metadata": {
    "userId": "user-uuid",
    "traceId": "trace-uuid",
    "spanId": "span-uuid"
  },
  "data": {
    // 이벤트별 페이로드
  }
}
```

### 4.2. 이벤트 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `eventId` | UUID | ✓ | 이벤트 고유 식별자 |
| `eventType` | String | ✓ | 이벤트 타입 (PascalCase) |
| `eventVersion` | String | ✓ | 스키마 버전 (Semantic Versioning) |
| `source` | String | ✓ | 이벤트 발행 서비스명 |
| `timestamp` | ISO8601 | ✓ | 이벤트 발생 시각 (UTC) |
| `correlationId` | UUID | ✓ | 요청 추적 ID |
| `causationId` | UUID | - | 원인 이벤트 ID |
| `metadata` | Object | - | 추가 메타데이터 |
| `data` | Object | ✓ | 이벤트 페이로드 |

## 5. 정책 이벤트 스키마

### 5.1. PolicyCreated 이벤트
```json
{
  "eventType": "PolicyCreated",
  "eventVersion": "1.0",
  "data": {
    "policyId": "uuid",
    "title": "정책명",
    "issuingOrganization": "발행기관",
    "category": "창업지원",
    "targetRegions": ["11", "41"],
    "targetIndustries": ["56", "62"],
    "fundingDetails": {
      "maxAmount": 50000000,
      "interestRate": 2.5,
      "repaymentPeriod": "5년"
    },
    "applicationPeriod": {
      "startDate": "2025-01-01",
      "endDate": "2025-12-31"
    },
    "qualityScore": 0.95,
    "status": "active"
  }
}
```

### 5.2. PolicyUpdated 이벤트
```json
{
  "eventType": "PolicyUpdated",
  "eventVersion": "1.0",
  "data": {
    "policyId": "uuid",
    "changes": {
      "title": {
        "from": "이전 제목",
        "to": "새로운 제목"
      },
      "status": {
        "from": "active",
        "to": "inactive"
      }
    },
    "updatedFields": ["title", "status"],
    "qualityScore": 0.92
  }
}
```

### 5.3. PolicyDeleted 이벤트
```json
{
  "eventType": "PolicyDeleted",
  "eventVersion": "1.0",
  "data": {
    "policyId": "uuid",
    "title": "삭제된 정책명",
    "reason": "expired",
    "deletedAt": "2025-09-17T10:30:00.000Z"
  }
}
```

## 6. 사용자 이벤트 스키마

### 6.1. UserRegistered 이벤트
```json
{
  "eventType": "UserRegistered",
  "eventVersion": "1.0",
  "data": {
    "userId": "uuid",
    "email": "user@example.com",
    "businessType": "소상공인",
    "regionCode": "11",
    "industryCode": "56",
    "registrationSource": "web",
    "emailVerified": false
  }
}
```

### 6.2. UserProfileUpdated 이벤트
```json
{
  "eventType": "UserProfileUpdated",
  "eventVersion": "1.0",
  "data": {
    "userId": "uuid",
    "changes": {
      "businessInfo": {
        "employeeCount": {
          "from": 3,
          "to": 5
        }
      },
      "financialInfo": {
        "annualRevenue": {
          "from": 50000000,
          "to": 80000000
        }
      }
    },
    "updatedFields": ["businessInfo.employeeCount", "financialInfo.annualRevenue"]
  }
}
```

### 6.3. UserLoggedIn 이벤트
```json
{
  "eventType": "UserLoggedIn",
  "eventVersion": "1.0",
  "data": {
    "userId": "uuid",
    "sessionId": "session-uuid",
    "ipAddress": "192.168.1.1",
    "userAgent": "Mozilla/5.0...",
    "loginMethod": "email_password",
    "deviceInfo": {
      "type": "desktop",
      "os": "Windows 10",
      "browser": "Chrome 118"
    }
  }
}
```

## 7. 추천 이벤트 스키마

### 7.1. RecommendationRequested 이벤트
```json
{
  "eventType": "RecommendationRequested",
  "eventVersion": "1.0",
  "data": {
    "recommendationId": "uuid",
    "userId": "uuid",
    "sessionId": "session-uuid",
    "query": "경기도 카페 창업 운영자금",
    "userProfile": {
      "businessType": "소상공인",
      "regionCode": "41",
      "industryCode": "56"
    },
    "searchOptions": {
      "maxResults": 10,
      "includeExpired": false
    }
  }
}
```

### 7.2. RecommendationGenerated 이벤트
```json
{
  "eventType": "RecommendationGenerated",
  "eventVersion": "1.0",
  "data": {
    "recommendationId": "uuid",
    "userId": "uuid",
    "results": [
      {
        "policyId": "policy-uuid",
        "rank": 1,
        "relevanceScore": 0.95,
        "confidenceScore": 0.88
      }
    ],
    "searchMetadata": {
      "totalPoliciesSearched": 1247,
      "processingTimeMs": 245,
      "searchStrategy": "hybrid_rag_kg"
    },
    "modelVersions": {
      "embedding": "sentence-transformers-v2.1",
      "llm": "gpt-4o-2024-08-06"
    }
  }
}
```

### 7.3. RecommendationFeedbackReceived 이벤트
```json
{
  "eventType": "RecommendationFeedbackReceived",
  "eventVersion": "1.0",
  "data": {
    "recommendationId": "uuid",
    "userId": "uuid",
    "feedback": {
      "overallRating": 4,
      "helpfulPolicies": ["policy-uuid-1"],
      "notHelpfulPolicies": ["policy-uuid-2"],
      "comments": "첫 번째 추천이 정확했습니다.",
      "appliedPolicies": ["policy-uuid-1"]
    },
    "feedbackTimestamp": "2025-09-17T10:35:00.000Z"
  }
}
```

## 8. 시스템 이벤트 스키마

### 8.1. ServiceHealthChanged 이벤트
```json
{
  "eventType": "ServiceHealthChanged",
  "eventVersion": "1.0",
  "data": {
    "serviceName": "recommendation-service",
    "instanceId": "rec-svc-001",
    "healthStatus": "unhealthy",
    "previousStatus": "healthy",
    "healthChecks": {
      "database": "healthy",
      "vectorDb": "unhealthy",
      "cache": "healthy"
    },
    "errorDetails": {
      "component": "milvus",
      "error": "Connection timeout",
      "errorCode": "CONN_TIMEOUT"
    }
  }
}
```

### 8.2. DataSyncCompleted 이벤트
```json
{
  "eventType": "DataSyncCompleted",
  "eventVersion": "1.0",
  "data": {
    "syncJobId": "sync-uuid",
    "syncType": "policy_vectorization",
    "sourceSystem": "postgresql",
    "targetSystem": "milvus",
    "recordsProcessed": 1247,
    "recordsSucceeded": 1245,
    "recordsFailed": 2,
    "processingTimeMs": 45000,
    "failedRecords": [
      {
        "recordId": "policy-uuid-1",
        "error": "Invalid embedding dimension"
      }
    ]
  }
}
```

## 9. 보안 이벤트 스키마

### 9.1. AuthenticationFailed 이벤트
```json
{
  "eventType": "AuthenticationFailed",
  "eventVersion": "1.0",
  "data": {
    "attemptId": "uuid",
    "email": "user@example.com",
    "ipAddress": "192.168.1.1",
    "userAgent": "Mozilla/5.0...",
    "failureReason": "invalid_password",
    "attemptCount": 3,
    "isBlocked": false,
    "geolocation": {
      "country": "KR",
      "city": "Seoul"
    }
  }
}
```

### 9.2. SuspiciousActivityDetected 이벤트
```json
{
  "eventType": "SuspiciousActivityDetected",
  "eventVersion": "1.0",
  "data": {
    "activityId": "uuid",
    "userId": "uuid",
    "activityType": "rapid_api_calls",
    "severity": "medium",
    "details": {
      "requestCount": 1000,
      "timeWindowMinutes": 5,
      "endpoint": "/api/v1/recommendations"
    },
    "riskScore": 0.75,
    "actionTaken": "rate_limit_applied"
  }
}
```

## 10. 이벤트 버전 관리

### 10.1. 스키마 진화 규칙

#### 호환 가능한 변경 (Minor Version)
- 새로운 선택적 필드 추가
- 기존 필드의 설명 변경
- 열거형 값 추가

#### 호환 불가능한 변경 (Major Version)
- 필수 필드 제거
- 필드 타입 변경
- 필드명 변경
- 열거형 값 제거

### 10.2. 버전 관리 예시
```json
// v1.0 - 초기 버전
{
  "eventType": "PolicyCreated",
  "eventVersion": "1.0",
  "data": {
    "policyId": "uuid",
    "title": "정책명"
  }
}

// v1.1 - 호환 가능한 변경 (필드 추가)
{
  "eventType": "PolicyCreated",
  "eventVersion": "1.1",
  "data": {
    "policyId": "uuid",
    "title": "정책명",
    "description": "정책 설명" // 새로운 선택적 필드
  }
}

// v2.0 - 호환 불가능한 변경 (필드명 변경)
{
  "eventType": "PolicyCreated",
  "eventVersion": "2.0",
  "data": {
    "policyId": "uuid",
    "policyTitle": "정책명" // title -> policyTitle 변경
  }
}
```

## 11. 이벤트 처리 패턴

### 11.1. 이벤트 소싱 패턴
```python
class EventStore:
    async def append_event(self, stream_id: str, event: Event, expected_version: int):
        """이벤트 스트림에 이벤트 추가"""
        pass
    
    async def get_events(self, stream_id: str, from_version: int = 0) -> List[Event]:
        """이벤트 스트림에서 이벤트 조회"""
        pass

class PolicyAggregate:
    def __init__(self, policy_id: str):
        self.policy_id = policy_id
        self.version = 0
        self.uncommitted_events = []
    
    def create_policy(self, title: str, organization: str):
        """정책 생성 명령 처리"""
        event = PolicyCreated(
            policy_id=self.policy_id,
            title=title,
            issuing_organization=organization
        )
        self._apply_event(event)
        self.uncommitted_events.append(event)
    
    def _apply_event(self, event: Event):
        """이벤트 적용하여 상태 변경"""
        if isinstance(event, PolicyCreated):
            self.title = event.title
            self.issuing_organization = event.issuing_organization
        elif isinstance(event, PolicyUpdated):
            # 업데이트 로직
            pass
        
        self.version += 1
```

### 11.2. CQRS 패턴
```python
class PolicyCommandHandler:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    async def handle_create_policy(self, command: CreatePolicyCommand):
        """정책 생성 명령 처리"""
        aggregate = PolicyAggregate(command.policy_id)
        aggregate.create_policy(command.title, command.organization)
        
        # 이벤트 저장
        for event in aggregate.uncommitted_events:
            await self.event_store.append_event(
                stream_id=f"policy-{command.policy_id}",
                event=event,
                expected_version=aggregate.version - 1
            )

class PolicyProjection:
    def __init__(self, db: Database):
        self.db = db
    
    async def handle_policy_created(self, event: PolicyCreated):
        """PolicyCreated 이벤트 처리하여 읽기 모델 업데이트"""
        await self.db.execute("""
            INSERT INTO policy_read_model (policy_id, title, organization)
            VALUES (?, ?, ?)
        """, event.policy_id, event.title, event.issuing_organization)
```

## 12. 이벤트 모니터링 및 알림

### 12.1. 이벤트 메트릭
```python
from prometheus_client import Counter, Histogram, Gauge

# 이벤트 발행 메트릭
events_published = Counter('events_published_total', ['event_type', 'source'])
event_processing_time = Histogram('event_processing_seconds', ['event_type'])

# 이벤트 소비 메트릭
events_consumed = Counter('events_consumed_total', ['event_type', 'consumer'])
event_lag = Gauge('event_consumer_lag', ['topic', 'partition', 'consumer_group'])

# 에러 메트릭
event_processing_errors = Counter('event_processing_errors_total', ['event_type', 'error_type'])
```

### 12.2. 이벤트 알림 규칙
- **이벤트 처리 지연 > 5분**: 경고 알림
- **이벤트 처리 실패율 > 1%**: 즉시 알림
- **Dead Letter Queue 메시지 > 10개**: 경고 알림
- **특정 이벤트 타입 0개 > 1시간**: 모니터링 알림

## 13. 개발 및 테스트 가이드

### 13.1. 이벤트 테스트 패턴
```python
import pytest
from unittest.mock import AsyncMock

class TestPolicyEventHandlers:
    @pytest.mark.asyncio
    async def test_policy_created_event_handling(self):
        # Given
        event = PolicyCreated(
            policy_id="test-policy-id",
            title="테스트 정책",
            issuing_organization="테스트 기관"
        )
        
        mock_projection = AsyncMock()
        handler = PolicyProjectionHandler(mock_projection)
        
        # When
        await handler.handle(event)
        
        # Then
        mock_projection.update_policy.assert_called_once_with(
            policy_id="test-policy-id",
            title="테스트 정책",
            organization="테스트 기관"
        )
    
    @pytest.mark.asyncio
    async def test_event_schema_validation(self):
        # Given
        invalid_event_data = {
            "eventType": "PolicyCreated",
            "eventVersion": "1.0",
            # 필수 필드 누락
        }
        
        # When & Then
        with pytest.raises(ValidationError):
            PolicyCreated.parse_obj(invalid_event_data)
```

### 13.2. 이벤트 스키마 검증
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

class BaseEvent(BaseModel):
    eventId: str = Field(..., description="이벤트 고유 ID")
    eventType: str = Field(..., description="이벤트 타입")
    eventVersion: str = Field(..., regex=r"^\d+\.\d+$", description="스키마 버전")
    source: str = Field(..., description="이벤트 소스")
    timestamp: datetime = Field(..., description="이벤트 발생 시각")
    correlationId: str = Field(..., description="상관관계 ID")
    causationId: Optional[str] = Field(None, description="원인 이벤트 ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터")
    
    @validator('timestamp')
    def timestamp_must_be_utc(cls, v):
        if v.tzinfo is None:
            raise ValueError('timestamp must include timezone info')
        return v

class PolicyCreated(BaseEvent):
    eventType: str = Field("PolicyCreated", const=True)
    data: PolicyCreatedData
    
    class PolicyCreatedData(BaseModel):
        policyId: str = Field(..., description="정책 ID")
        title: str = Field(..., min_length=1, max_length=512, description="정책명")
        issuingOrganization: str = Field(..., description="발행기관")
        # ... 기타 필드들
```

---

**📋 관련 문서**
- [이중 트랙 파이프라인](../02_CORE_COMPONENTS/01_DUAL_TRACK_PIPELINE.md)
- [마이크로서비스 설계](../01_ARCHITECTURE/02_MICROSERVICES_DESIGN.md)
- [API 명세서](./API_CONTRACT.md)
- [데이터베이스 스키마](./DATABASE_SCHEMA.md)