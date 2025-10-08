# Policy Service Design Document

## 1. Overview

Policy Service는 이지스(Aegis) 시스템의 핵심 데이터 관리 서비스로, 정부 정책자금 정보의 **저장, 관리, 제공**을 담당합니다.

### 1.1 핵심 책임

1. **Data Pipeline으로부터 검증된 정책 데이터 수신** (이벤트 구독)
2. **정책 데이터 CRUD 작업** (생성, 조회, 수정, 삭제)
3. **정책 메타데이터 관리** (분류, 태그, 품질 점수)
4. **정책 버전 관리** (변경 이력, 롤백)
5. **정책 품질 관리** (검증, 중복 제거, 완성도)
6. **다른 서비스에 정책 데이터 제공** (API, 이벤트)

### 1.2 역할 명확화 (중요)

**Policy Service의 역할:**
- ✅ 정책 데이터의 CRUD 및 비즈니스 로직
- ✅ Data Pipeline이 발행하는 검증된 데이터 수신
- ✅ 정책 메타데이터 및 버전 관리
- ✅ 다른 서비스에 정책 정보 제공

**Policy Service가 하지 않는 것:**
- ❌ 외부 API 호출 및 데이터 수집 (Data Pipeline 담당)
- ❌ 웹 크롤링 및 스크래핑 (Data Pipeline 담당)
- ❌ 원시 데이터 파싱 및 변환 (Data Pipeline 담당)
- ❌ 검색 엔진 기능 (Search Service 담당)
- ❌ 추천 알고리즘 (Recommendation Service 담당)

### 1.3 설계 원칙

1. **단일 책임 원칙**: 정책 데이터 관리에만 집중
2. **이벤트 기반 아키텍처**: Data Pipeline과 느슨한 결합
3. **확장성**: 수평 확장 가능한 무상태 설계
4. **일관성**: shared-library를 통한 표준화
5. **관찰성**: 모든 주요 작업에 대한 로깅 및 메트릭

### 1.4 다른 서비스와의 역할 구분

| 서비스 | 역할 | 통신 방식 |
|--------|------|----------|
| **Data Pipeline** | 외부 데이터 수집, 검증, 변환 | Kafka (이벤트 발행) |
| **Policy Service** | 정책 CRUD, 메타데이터, 버전 관리 | Kafka (이벤트 구독/발행) |
| **Search Service** | 정책 검색, 인덱싱 | Kafka (이벤트 구독) |
| **Recommendation Service** | 정책 추천 알고리즘 | API 호출 + Kafka |
| **User Service** | 사용자 인증 및 관리 | API 호출 |

---

## 2. Shared Library Integration

이 서비스는 `aegis-shared` 공통 라이브러리를 적극 활용합니다.

### 2.1 사용하는 모듈

```python
from aegis_shared.database import BaseRepository, DatabaseManager, SchemaRegistry
from aegis_shared.auth import JWTHandler, AuthMiddleware, RBAC
from aegis_shared.messaging import EventPublisher, EventSubscriber, VersionedEvent
from aegis_shared.logging import get_logger, add_context
from aegis_shared.monitoring import track_metrics
from aegis_shared.errors import ErrorCode, ServiceException
from aegis_shared.cache import cache_result, RedisClient
from aegis_shared.config import get_config
```

### 2.2 왜 Shared Library를 사용하는가?

#### 2.2.1 BaseRepository로 CRUD 자동화

**Before (shared-library 없이):**
```python
# ❌ 문제점: 반복적인 CRUD 코드, 에러 처리 누락, 일관성 부족
class PolicyRepository:
    def __init__(self, session):
        self.session = session
    
    async def create(self, policy: Policy) -> Policy:
        self.session.add(policy)
        await self.session.commit()
        await self.session.refresh(policy)
        return policy
    
    async def get_by_id(self, policy_id: UUID) -> Optional[Policy]:
        result = await self.session.execute(
            select(Policy).where(Policy.id == policy_id)
        )
        return result.scalar_one_or_none()
    
    # ... 수십 개의 반복적인 메서드
```

**After (shared-library 사용):**
```python
# ✅ 장점: CRUD 자동 제공, 에러 처리 내장, 표준화
from aegis_shared.database import BaseRepository

class PolicyRepository(BaseRepository[Policy]):
    """BaseRepository 상속으로 기본 CRUD 자동 제공"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Policy)
    
    # create, get_by_id, update, delete, list, count 자동 제공
    
    # 도메인 특화 메서드만 추가
    async def find_by_organization(self, org: str) -> List[Policy]:
        result = await self.session.execute(
            select(Policy).where(Policy.issuing_organization == org)
        )
        return result.scalars().all()
```

**효과:**
- 코드 라인 수 80% 감소 (200줄 → 40줄)
- 에러 처리 자동화
- 트랜잭션 관리 자동화
- 모든 서비스에서 일관된 데이터 액세스

#### 2.2.2 이벤트 발행/구독 자동화

**Before:**
```python
# ❌ Kafka 클라이언트 직접 관리, 에러 처리 복잡
from aiokafka import AIOKafkaProducer
import json

producer = AIOKafkaProducer(bootstrap_servers='kafka:9092')
await producer.start()

try:
    message = json.dumps({
        'event_type': 'policy.created',
        'data': {'policy_id': str(policy.id)}
    })
    await producer.send('policy-events', message.encode())
finally:
    await producer.stop()
```

**After:**
```python
# ✅ 이벤트 발행/구독 자동화, 스키마 버전 관리
from aegis_shared.messaging import VersionedEventPublisher

event_publisher = VersionedEventPublisher()

await event_publisher.publish(
    topic="policy-events",
    event_type="policy.created",
    data={
        "policy_id": str(policy.id),
        "title": policy.title
    },
    version="1.0.0",  # 스키마 버전 관리
    key=f"policy-{policy.id}"
)
```

**효과:**
- Kafka 연결 관리 자동화
- 스키마 버전 관리 내장
- 재시도 로직 자동 적용
- 에러 처리 표준화

#### 2.2.3 중앙 에러 코드 레지스트리

**Before:**
```python
# ❌ 각 서비스마다 다른 에러 코드, 일관성 없음
raise Exception("Policy not found")  # 불명확
raise HTTPException(status_code=404, detail="Not found")  # 표준화 안됨
```

**After:**
```python
# ✅ 중앙 에러 코드 레지스트리 사용
from aegis_shared.errors import ErrorCode, EntityNotFoundError

raise EntityNotFoundError(
    error_code=ErrorCode.ENTITY_NOT_FOUND,
    message=f"Policy not found: {policy_id}",
    details={"policy_id": str(policy_id)}
)
```

**효과:**
- 프론트엔드에서 에러 코드 기반 처리 가능
- 다국어 지원 용이
- 에러 추적 및 모니터링 표준화
- 모든 서비스에서 일관된 에러 응답

#### 2.2.4 구조화된 로깅

**Before:**
```python
# ❌ 비구조화된 로깅, 검색 어려움
import logging
logger = logging.getLogger(__name__)

logger.info(f"Policy created: {policy.id}")
```

**After:**
```python
# ✅ 구조화된 로깅, 컨텍스트 자동 추가
from aegis_shared.logging import get_logger, add_context

logger = get_logger(__name__)

logger.info(
    "policy_created",
    policy_id=str(policy.id),
    title=policy.title,
    organization=policy.issuing_organization
)
```

**효과:**
- Elasticsearch에서 쉽게 검색 가능
- request_id, user_id 자동 추가
- 로그 집계 및 분석 용이

---

## 3. Architecture

### 3.1 서비스 아키텍처

```mermaid
graph TB
    subgraph "External Systems"
        DATA_PIPELINE[Data Pipeline Service<br/>데이터 수집 및 검증]
    end
    
    subgraph "Message Queue"
        KAFKA[Apache Kafka<br/>KRaft Mode]
    end
    
    subgraph "Policy Service"
        subgraph "Event Layer"
            EVENT_SUB[Event Subscriber<br/>Data Pipeline 이벤트 구독]
            EVENT_PUB[Event Publisher<br/>정책 변경 이벤트 발행]
        end
        
        subgraph "API Layer"
            CRUD_API[CRUD API<br/>정책 생성/수정/삭제/조회]
            SEARCH_API[Search API<br/>정책 검색 및 필터링]
            VERSION_API[Version API<br/>버전 관리]
            ADMIN_API[Admin API<br/>관리 기능]
        end
        
        subgraph "Business Logic"
            POLICY_SVC[Policy Service<br/>핵심 비즈니스 로직]
            METADATA_SVC[Metadata Service<br/>메타데이터 관리]
            VERSION_SVC[Version Service<br/>버전 관리]
            QUALITY_SVC[Quality Service<br/>품질 관리]
        end
        
        subgraph "Data Access"
            POLICY_REPO[Policy Repository<br/>BaseRepository 상속]
            METADATA_REPO[Metadata Repository]
            VERSION_REPO[Version Repository]
        end
    end
    
    subgraph "Data Storage"
        POSTGRES[(PostgreSQL<br/>Source of Truth)]
        ELASTICSEARCH[(Elasticsearch<br/>검색 인덱스)]
        REDIS[(Redis<br/>캐시)]
    end
    
    subgraph "Other Services"
        SEARCH_SVC[Search Service]
        REC_SVC[Recommendation Service]
        USER_SVC[User Service]
    end
    
    %% Data Pipeline → Kafka → Policy Service
    DATA_PIPELINE -->|policy.validated 이벤트| KAFKA
    KAFKA -->|구독| EVENT_SUB
    EVENT_SUB --> POLICY_SVC
    
    %% API Layer → Business Logic
    CRUD_API --> POLICY_SVC
    SEARCH_API --> POLICY_SVC
    VERSION_API --> VERSION_SVC
    ADMIN_API --> POLICY_SVC
    
    %% Business Logic 내부
    POLICY_SVC --> METADATA_SVC
    POLICY_SVC --> VERSION_SVC
    POLICY_SVC --> QUALITY_SVC
    
    %% Business Logic → Data Access
    POLICY_SVC --> POLICY_REPO
    METADATA_SVC --> METADATA_REPO
    VERSION_SVC --> VERSION_REPO
    
    %% Data Access → Storage
    POLICY_REPO --> POSTGRES
    METADATA_REPO --> POSTGRES
    VERSION_REPO --> POSTGRES
    
    %% Caching & Indexing
    POLICY_SVC --> REDIS
    POLICY_SVC --> ELASTICSEARCH
    
    %% Event Publishing
    POLICY_SVC --> EVENT_PUB
    EVENT_PUB -->|policy.created/updated/deleted| KAFKA
    KAFKA --> SEARCH_SVC
    KAFKA --> REC_SVC
    KAFKA --> USER_SVC
```

### 3.2 데이터 흐름

```mermaid
sequenceDiagram
    participant DataPipeline as Data Pipeline
    participant Kafka as Apache Kafka
    participant PolicyService as Policy Service
    participant PostgreSQL as PostgreSQL
    participant Redis as Redis
    participant Elasticsearch as Elasticsearch
    participant OtherServices as Other Services
    
    Note over DataPipeline,OtherServices: 1. Data Pipeline이 데이터 수집 및 검증
    DataPipeline->>DataPipeline: 외부 API/웹 크롤링
    DataPipeline->>DataPipeline: 데이터 검증 및 변환
    DataPipeline->>Kafka: policy.validated 이벤트 발행
    
    Note over DataPipeline,OtherServices: 2. Policy Service가 검증된 데이터 수신
    Kafka->>PolicyService: policy.validated 이벤트
    PolicyService->>PolicyService: 중복 검사
    PolicyService->>PostgreSQL: 정책 데이터 저장
    PolicyService->>Redis: 캐시 저장
    PolicyService->>Elasticsearch: 검색 인덱스 업데이트
    
    Note over DataPipeline,OtherServices: 3. 다른 서비스들에게 알림
    PolicyService->>Kafka: policy.created 이벤트 발행
    Kafka->>OtherServices: policy.created 이벤트
    OtherServices->>OtherServices: 캐시 업데이트, 인덱스 재구축
```

### 3.3 컴포넌트 다이어그램

```mermaid
graph LR
    subgraph "Policy Service Components"
        A[Event Subscriber] --> B[Event Handler]
        B --> C[Policy Service]
        C --> D[Policy Repository]
        C --> E[Metadata Service]
        C --> F[Version Service]
        C --> G[Quality Service]
        
        H[CRUD API] --> C
        I[Search API] --> C
        J[Version API] --> F
        K[Admin API] --> C
        
        C --> L[Event Publisher]
    end
```



## 4. Components and Interfaces

### 4.1 Event Subscription Layer

#### 4.1.1 Data Pipeline Event Subscriber

```python
from typing import Dict, Any, List
from aegis_shared.messaging import EventSubscriber
from aegis_shared.logging import get_logger
from aegis_shared.errors import ErrorCode, ServiceException
from datetime import datetime

logger = get_logger(__name__)

class PolicyEventSubscriber:
    """Data Pipeline 이벤트 구독자"""
    
    def __init__(
        self,
        kafka_bootstrap_servers: str,
        policy_service: 'PolicyService'
    ):
        self.subscriber = EventSubscriber(
            bootstrap_servers=kafka_bootstrap_servers,
            group_id='policy-service-consumer',
            topics=['data-pipeline-events']
        )
        self.policy_service = policy_service
        self.logger = get_logger(__name__)
    
    async def start_consuming(self):
        """이벤트 구독 시작"""
        self.logger.info("starting_policy_event_subscription")
        
        async for event in self.subscriber.consume():
            try:
                await self.handle_event(event)
            except Exception as e:
                self.logger.error(
                    "event_handling_failed",
                    event_type=event.get('event_type'),
                    error=str(e),
                    exc_info=True
                )
    
    async def handle_event(self, event: Dict[str, Any]):
        """이벤트 처리 라우팅"""
        event_type = event.get('event_type')
        
        handlers = {
            'policy.validated': self.handle_policy_validated,
            'policy.quality_updated': self.handle_quality_updated,
            'data.consistency_check': self.handle_consistency_check
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(event)
        else:
            self.logger.warning(
                "unknown_event_type",
                event_type=event_type
            )
    
    async def handle_policy_validated(self, event: Dict[str, Any]):
        """Data Pipeline에서 검증된 정책 데이터 처리"""
        data = event.get('data', {})
        
        self.logger.info(
            "received_validated_policy",
            policy_title=data.get('title'),
            source=data.get('source_system')
        )
        
        try:
            policy_id = data.get('policy_id')
            
            if policy_id:
                # 기존 정책 업데이트
                await self.policy_service.update_from_pipeline(policy_id, data)
            else:
                # 새 정책 생성
                await self.policy_service.create_from_pipeline(data)
                
        except Exception as e:
            self.logger.error(
                "failed_to_process_validated_policy",
                error=str(e),
                exc_info=True
            )
            raise
    
    async def handle_quality_updated(self, event: Dict[str, Any]):
        """품질 점수 업데이트 이벤트 처리"""
        data = event.get('data', {})
        policy_id = data.get('policy_id')
        quality_score = data.get('quality_score')
        
        if policy_id and quality_score is not None:
            await self.policy_service.update_quality_score(
                policy_id,
                quality_score
            )
    
    async def handle_consistency_check(self, event: Dict[str, Any]):
        """데이터 일관성 검사 이벤트 처리"""
        data = event.get('data', {})
        inconsistencies = data.get('inconsistencies', [])
        
        if inconsistencies:
            self.logger.warning(
                "data_inconsistencies_detected",
                count=len(inconsistencies)
            )
            await self.policy_service.resolve_inconsistencies(
                inconsistencies
            )
```

#### 4.1.2 Event Handler

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class PolicyDataFromPipeline(BaseModel):
    """Data Pipeline으로부터 받은 정책 데이터"""
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    issuing_organization: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: List[str] = []
    target_regions: List[str] = []
    target_industries: List[str] = []
    target_business_types: List[str] = []
    funding_type: Optional[str] = None
    min_funding_amount: Optional[int] = None
    max_funding_amount: Optional[int] = None
    interest_rate: Optional[float] = None
    application_start_date: Optional[datetime] = None
    application_end_date: Optional[datetime] = None
    application_url: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    original_url: Optional[str] = None
    source_system: str
    quality_score: float = 0.0
    raw_data: Dict[str, Any] = {}
    
    @validator('quality_score')
    def validate_quality_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Quality score must be between 0 and 1')
        return v

class PolicyEventHandler:
    """정책 이벤트 처리기"""
    
    def __init__(
        self,
        policy_repository: 'PolicyRepository',
        metadata_service: 'MetadataService'
    ):
        self.policy_repo = policy_repository
        self.metadata_service = metadata_service
        self.logger = get_logger(__name__)
    
    async def process_validated_policy(
        self,
        data: PolicyDataFromPipeline
    ) -> Policy:
        """검증된 정책 데이터 처리"""
        
        # 중복 검사
        existing_policy = await self.find_duplicate(data)
        
        if existing_policy:
            self.logger.info(
                "updating_existing_policy",
                policy_id=str(existing_policy.id),
                title=data.title
            )
            return await self.update_existing_policy(existing_policy, data)
        else:
            self.logger.info(
                "creating_new_policy",
                title=data.title,
                organization=data.issuing_organization
            )
            return await self.create_new_policy(data)
    
    async def find_duplicate(
        self,
        data: PolicyDataFromPipeline
    ) -> Optional[Policy]:
        """중복 정책 검색"""
        similar_policies = await self.policy_repo.find_by_title_and_org(
            title=data.title,
            organization=data.issuing_organization
        )
        
        return similar_policies[0] if similar_policies else None
    
    async def create_new_policy(
        self,
        data: PolicyDataFromPipeline
    ) -> Policy:
        """새 정책 생성"""
        
        # 메타데이터 생성
        metadata = await self.metadata_service.generate_metadata_from_data(data)
        
        policy = Policy(
            title=data.title,
            content=data.content,
            issuing_organization=data.issuing_organization,
            category=data.category,
            subcategory=data.subcategory,
            tags=data.tags,
            target_regions=data.target_regions,
            target_industries=data.target_industries,
            target_business_types=data.target_business_types,
            funding_type=data.funding_type,
            min_funding_amount=data.min_funding_amount,
            max_funding_amount=data.max_funding_amount,
            interest_rate=data.interest_rate,
            application_start_date=data.application_start_date,
            application_end_date=data.application_end_date,
            application_url=data.application_url,
            contact_phone=data.contact_phone,
            contact_email=data.contact_email,
            original_url=data.original_url,
            source_system=data.source_system,
            quality_score=data.quality_score,
            metadata=metadata,
            raw_data=data.raw_data,
            status=PolicyStatus.ACTIVE,
            version=1
        )
        
        return await self.policy_repo.create(policy)
    
    async def update_existing_policy(
        self,
        existing_policy: Policy,
        data: PolicyDataFromPipeline
    ) -> Policy:
        """기존 정책 업데이트"""
        changes = {}
        
        # 변경사항 감지
        if existing_policy.content != data.content:
            changes['content'] = data.content
        
        if existing_policy.quality_score != data.quality_score:
            changes['quality_score'] = data.quality_score
        
        if existing_policy.application_end_date != data.application_end_date:
            changes['application_end_date'] = data.application_end_date
        
        if changes:
            changes['updated_at'] = datetime.utcnow()
            changes['version'] = existing_policy.version + 1
            
            self.logger.info(
                "policy_updated",
                policy_id=str(existing_policy.id),
                changed_fields=list(changes.keys())
            )
        
        return await self.policy_repo.update(existing_policy.id, **changes)
```

### 4.2 API Layer

#### 4.2.1 CRUD API

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID
from aegis_shared.auth import require_role, get_current_user
from aegis_shared.errors import EntityNotFoundError, DuplicateEntityError
from aegis_shared.monitoring import track_metrics

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])

@router.post(
    "/",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED
)
@track_metrics("policy_create")
async def create_policy(
    request: CreatePolicyRequest,
    policy_service: PolicyService = Depends(get_policy_service),
    current_user: dict = Depends(get_current_user)
):
    """
    새 정책 생성 (관리자 전용)
    
    Note: 일반적으로 정책은 Data Pipeline을 통해 자동 생성됩니다.
    이 API는 수동 생성이 필요한 경우에만 사용합니다.
    """
    try:
        policy = await policy_service.create_policy(request, current_user)
        return PolicyResponse.from_orm(policy)
    except DuplicateEntityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.to_dict()
        )

@router.get("/{policy_id}", response_model=PolicyResponse)
@track_metrics("policy_get")
async def get_policy(
    policy_id: UUID,
    policy_service: PolicyService = Depends(get_policy_service)
):
    """정책 상세 조회"""
    policy = await policy_service.get_policy(policy_id)
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": ErrorCode.ENTITY_NOT_FOUND,
                "message": "Policy not found",
                "details": {"policy_id": str(policy_id)}
            }
        )
    
    return PolicyResponse.from_orm(policy)

@router.get("/", response_model=PaginatedPolicyResponse)
@track_metrics("policy_list")
async def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    status: Optional[PolicyStatus] = None,
    organization: Optional[str] = None,
    policy_service: PolicyService = Depends(get_policy_service)
):
    """정책 목록 조회"""
    filters = {}
    if category:
        filters['category'] = category
    if status:
        filters['status'] = status
    if organization:
        filters['issuing_organization'] = organization
    
    policies = await policy_service.list_policies(skip, limit, filters)
    total = await policy_service.count_policies(filters)
    
    return PaginatedPolicyResponse.create(
        items=[PolicyResponse.from_orm(p) for p in policies],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

@router.put("/{policy_id}", response_model=PolicyResponse)
@track_metrics("policy_update")
@require_role(["admin", "moderator"])
async def update_policy(
    policy_id: UUID,
    request: UpdatePolicyRequest,
    policy_service: PolicyService = Depends(get_policy_service),
    current_user: dict = Depends(get_current_user)
):
    """정책 업데이트 (관리자/모더레이터 전용)"""
    try:
        policy = await policy_service.update_policy(
            policy_id,
            request,
            current_user
        )
        return PolicyResponse.from_orm(policy)
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict()
        )

@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
@track_metrics("policy_delete")
@require_role(["admin"])
async def delete_policy(
    policy_id: UUID,
    policy_service: PolicyService = Depends(get_policy_service),
    current_user: dict = Depends(get_current_user)
):
    """정책 삭제 (소프트 삭제, 관리자 전용)"""
    await policy_service.delete_policy(policy_id, current_user)
```

#### 4.2.2 Search API

```python
@router.get("/search", response_model=PaginatedPolicyResponse)
@track_metrics("policy_search")
async def search_policies(
    q: str = Query(..., min_length=1, max_length=200),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    regions: Optional[List[str]] = Query(None),
    policy_service: PolicyService = Depends(get_policy_service)
):
    """정책 검색"""
    search_params = {
        'query': q,
        'category': category,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'regions': regions
    }
    
    policies = await policy_service.search_policies(
        search_params,
        skip,
        limit
    )
    total = await policy_service.count_search_results(search_params)
    
    return PaginatedPolicyResponse.create(
        items=[PolicyResponse.from_orm(p) for p in policies],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )
```



### 4.3 Business Logic Layer

#### 4.3.1 Policy Service

```python
from aegis_shared.database import BaseRepository
from aegis_shared.messaging import VersionedEventPublisher
from aegis_shared.logging import get_logger, add_context
from aegis_shared.errors import EntityNotFoundError, DuplicateEntityError, ErrorCode
from aegis_shared.monitoring import track_metrics
from aegis_shared.cache import cache_result, RedisClient

logger = get_logger(__name__)

class PolicyRepository(BaseRepository[Policy]):
    """
    BaseRepository를 상속받아 기본 CRUD 자동 제공
    - create, get_by_id, update, delete, list, count
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Policy)
    
    async def find_by_title_and_org(
        self,
        title: str,
        organization: str
    ) -> List[Policy]:
        """제목과 발행기관으로 검색"""
        result = await self.session.execute(
            select(Policy)
            .where(Policy.title == title)
            .where(Policy.issuing_organization == organization)
            .where(Policy.status != PolicyStatus.ARCHIVED)
        )
        return result.scalars().all()
    
    async def find_active_policies(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Policy]:
        """활성 정책 목록"""
        return await self.list(
            skip=skip,
            limit=limit,
            filters={"status": PolicyStatus.ACTIVE}
        )
    
    async def find_by_organization(
        self,
        organization: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Policy]:
        """발행기관별 정책 조회"""
        result = await self.session.execute(
            select(Policy)
            .where(Policy.issuing_organization == organization)
            .where(Policy.status == PolicyStatus.ACTIVE)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

class PolicyService:
    """정책 서비스 - 핵심 비즈니스 로직"""
    
    def __init__(
        self,
        policy_repo: PolicyRepository,
        event_publisher: VersionedEventPublisher,
        metadata_service: 'MetadataService',
        version_service: 'VersionService',
        quality_service: 'QualityService',
        redis_client: RedisClient
    ):
        self.policy_repo = policy_repo
        self.event_publisher = event_publisher
        self.metadata_service = metadata_service
        self.version_service = version_service
        self.quality_service = quality_service
        self.redis_client = redis_client
    
    @track_metrics("policy_create")
    async def create_policy(
        self,
        policy_data: CreatePolicyRequest,
        current_user: dict
    ) -> Policy:
        """새 정책 생성 (수동)"""
        add_context(
            operation="create_policy",
            user_id=current_user.get('user_id')
        )
        
        async with self.policy_repo.session.begin():
            # 중복 검사
            existing_policy = await self.find_duplicate_policy(policy_data)
            if existing_policy:
                raise DuplicateEntityError(
                    error_code=ErrorCode.DUPLICATE_ENTITY,
                    message="Policy already exists",
                    details={"existing_id": str(existing_policy.id)}
                )
            
            # 메타데이터 생성
            metadata = await self.metadata_service.generate_metadata(
                policy_data
            )
            
            # 정책 생성
            policy = Policy(
                title=policy_data.title,
                content=policy_data.content,
                issuing_organization=policy_data.issuing_organization,
                category=policy_data.category,
                funding_type=policy_data.funding_type,
                max_funding_amount=policy_data.max_funding_amount,
                metadata=metadata,
                status=PolicyStatus.ACTIVE,
                version=1
            )
            
            # 저장
            saved_policy = await self.policy_repo.create(policy)
            
            # 버전 생성
            await self.version_service.create_version(saved_policy)
            
            # 이벤트 발행
            await self.event_publisher.publish(
                topic="policy-events",
                event_type="policy.created",
                data={
                    "policy_id": str(saved_policy.id),
                    "title": saved_policy.title,
                    "organization": saved_policy.issuing_organization,
                    "source": "manual",
                    "created_by": current_user.get('user_id')
                },
                version="1.0.0",
                key=f"policy-{saved_policy.id}"
            )
            
            logger.info(
                "policy_created",
                policy_id=str(saved_policy.id),
                title=saved_policy.title,
                created_by=current_user.get('user_id')
            )
            
            return saved_policy
    
    async def create_from_pipeline(
        self,
        data: Dict[str, Any]
    ) -> Policy:
        """Data Pipeline으로부터 정책 생성"""
        add_context(operation="create_from_pipeline")
        
        pipeline_data = PolicyDataFromPipeline(**data)
        event_handler = PolicyEventHandler(
            self.policy_repo,
            self.metadata_service
        )
        
        policy = await event_handler.process_validated_policy(pipeline_data)
        
        # 버전 생성
        await self.version_service.create_version(policy)
        
        # 캐시 무효화
        await self.redis_client.delete(f"policy:{policy.id}")
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="policy-events",
            event_type="policy.created",
            data={
                "policy_id": str(policy.id),
                "title": policy.title,
                "organization": policy.issuing_organization,
                "source": "data_pipeline"
            },
            version="1.0.0",
            key=f"policy-{policy.id}"
        )
        
        logger.info(
            "policy_created_from_pipeline",
            policy_id=str(policy.id),
            title=policy.title
        )
        
        return policy
    
    async def update_from_pipeline(
        self,
        policy_id: UUID,
        data: Dict[str, Any]
    ) -> Policy:
        """Data Pipeline으로부터 정책 업데이트"""
        existing_policy = await self.policy_repo.get_by_id(policy_id)
        
        if not existing_policy:
            raise EntityNotFoundError(
                error_code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Policy not found: {policy_id}",
                details={"policy_id": str(policy_id)}
            )
        
        pipeline_data = PolicyDataFromPipeline(**data)
        event_handler = PolicyEventHandler(
            self.policy_repo,
            self.metadata_service
        )
        
        updated_policy = await event_handler.update_existing_policy(
            existing_policy,
            pipeline_data
        )
        
        # 버전 생성
        await self.version_service.create_version(updated_policy)
        
        # 캐시 무효화
        await self.redis_client.delete(f"policy:{policy_id}")
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="policy-events",
            event_type="policy.updated",
            data={
                "policy_id": str(updated_policy.id),
                "title": updated_policy.title,
                "version": updated_policy.version
            },
            version="1.0.0",
            key=f"policy-{updated_policy.id}"
        )
        
        return updated_policy
    
    @cache_result(ttl=300, key_prefix="policy")
    async def get_policy(self, policy_id: UUID) -> Optional[Policy]:
        """정책 조회 (캐싱)"""
        return await self.policy_repo.get_by_id(policy_id)
    
    async def list_policies(
        self,
        skip: int,
        limit: int,
        filters: Dict[str, Any]
    ) -> List[Policy]:
        """정책 목록 조회"""
        return await self.policy_repo.list(skip, limit, filters)
    
    async def count_policies(self, filters: Dict[str, Any]) -> int:
        """정책 개수 조회"""
        return await self.policy_repo.count(filters)
    
    async def update_policy(
        self,
        policy_id: UUID,
        policy_data: UpdatePolicyRequest,
        current_user: dict
    ) -> Policy:
        """정책 업데이트"""
        existing_policy = await self.policy_repo.get_by_id(policy_id)
        
        if not existing_policy:
            raise EntityNotFoundError(
                error_code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Policy not found: {policy_id}"
            )
        
        # 변경사항 적용
        update_data = policy_data.dict(exclude_unset=True)
        update_data['version'] = existing_policy.version + 1
        update_data['updated_at'] = datetime.utcnow()
        
        updated_policy = await self.policy_repo.update(policy_id, **update_data)
        
        # 버전 생성
        await self.version_service.create_version(updated_policy)
        
        # 캐시 무효화
        await self.redis_client.delete(f"policy:{policy_id}")
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="policy-events",
            event_type="policy.updated",
            data={
                "policy_id": str(policy_id),
                "updated_by": current_user.get('user_id'),
                "changes": list(update_data.keys())
            },
            version="1.0.0",
            key=f"policy-{policy_id}"
        )
        
        return updated_policy
    
    async def delete_policy(
        self,
        policy_id: UUID,
        current_user: dict
    ):
        """정책 삭제 (소프트 삭제)"""
        existing_policy = await self.policy_repo.get_by_id(policy_id)
        
        if not existing_policy:
            raise EntityNotFoundError(
                error_code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Policy not found: {policy_id}"
            )
        
        # 소프트 삭제
        await self.policy_repo.update(
            policy_id,
            status=PolicyStatus.ARCHIVED,
            updated_at=datetime.utcnow()
        )
        
        # 캐시 무효화
        await self.redis_client.delete(f"policy:{policy_id}")
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="policy-events",
            event_type="policy.deleted",
            data={
                "policy_id": str(policy_id),
                "deleted_by": current_user.get('user_id')
            },
            version="1.0.0",
            key=f"policy-{policy_id}"
        )
        
        logger.info(
            "policy_deleted",
            policy_id=str(policy_id),
            deleted_by=current_user.get('user_id')
        )
    
    async def update_quality_score(
        self,
        policy_id: UUID,
        quality_score: float
    ):
        """품질 점수 업데이트"""
        await self.policy_repo.update(
            policy_id,
            quality_score=quality_score
        )
        
        # 캐시 무효화
        await self.redis_client.delete(f"policy:{policy_id}")
    
    async def resolve_inconsistencies(
        self,
        inconsistencies: List[Dict[str, Any]]
    ):
        """데이터 불일치 해결"""
        for inconsistency in inconsistencies:
            policy_id = inconsistency.get('policy_id')
            correct_data = inconsistency.get('correct_data')
            
            if policy_id and correct_data:
                await self.policy_repo.update(policy_id, **correct_data)
                await self.redis_client.delete(f"policy:{policy_id}")
                
                logger.info(
                    "inconsistency_resolved",
                    policy_id=str(policy_id)
                )
```

#### 4.3.2 Metadata Service

```python
class MetadataService:
    """정책 메타데이터 관리"""
    
    async def generate_metadata(
        self,
        policy_data: CreatePolicyRequest
    ) -> Dict[str, Any]:
        """정책 메타데이터 생성"""
        metadata = {
            'generated_at': datetime.utcnow().isoformat(),
            'word_count': len(policy_data.content.split()),
            'has_funding_info': bool(policy_data.max_funding_amount),
            'completeness_score': self.calculate_completeness(policy_data)
        }
        
        return metadata
    
    async def generate_metadata_from_data(
        self,
        data: PolicyDataFromPipeline
    ) -> Dict[str, Any]:
        """Pipeline 데이터로부터 메타데이터 생성"""
        metadata = {
            'generated_at': datetime.utcnow().isoformat(),
            'word_count': len(data.content.split()),
            'has_funding_info': bool(data.max_funding_amount),
            'has_deadline': bool(data.application_end_date),
            'completeness_score': self.calculate_completeness_from_data(data),
            'source_system': data.source_system
        }
        
        return metadata
    
    def calculate_completeness(
        self,
        policy_data: CreatePolicyRequest
    ) -> float:
        """정책 정보 완성도 계산"""
        required_fields = [
            policy_data.title,
            policy_data.content,
            policy_data.issuing_organization,
            policy_data.category,
            policy_data.funding_type
        ]
        
        filled_fields = sum(1 for field in required_fields if field)
        return filled_fields / len(required_fields)
    
    def calculate_completeness_from_data(
        self,
        data: PolicyDataFromPipeline
    ) -> float:
        """Pipeline 데이터 완성도 계산"""
        required_fields = [
            data.title,
            data.content,
            data.issuing_organization,
            data.category,
            data.funding_type,
            data.application_end_date,
            data.contact_phone or data.contact_email
        ]
        
        filled_fields = sum(1 for field in required_fields if field)
        return filled_fields / len(required_fields)
```

#### 4.3.3 Version Service

```python
class VersionService:
    """정책 버전 관리"""
    
    def __init__(self, version_repo: 'VersionRepository'):
        self.version_repo = version_repo
    
    async def create_version(self, policy: Policy):
        """정책 버전 생성"""
        version = PolicyVersion(
            policy_id=policy.id,
            version_number=policy.version,
            policy_data=policy.dict(),
            created_at=datetime.utcnow()
        )
        
        await self.version_repo.create(version)
        
        logger.info(
            "version_created",
            policy_id=str(policy.id),
            version_number=version.version_number
        )
    
    async def get_version_history(
        self,
        policy_id: UUID
    ) -> List[PolicyVersion]:
        """정책 버전 히스토리 조회"""
        return await self.version_repo.find_by_policy_id(policy_id)
    
    async def rollback_to_version(
        self,
        policy_id: UUID,
        version_number: int
    ) -> Policy:
        """특정 버전으로 롤백"""
        version = await self.version_repo.find_by_policy_and_version(
            policy_id,
            version_number
        )
        
        if not version:
            raise EntityNotFoundError(
                error_code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Version {version_number} not found"
            )
        
        # 버전 데이터로 정책 복원
        policy_data = version.policy_data
        # ... 복원 로직
        
        return policy
```

#### 4.3.4 Quality Service

```python
class QualityService:
    """정책 품질 관리"""
    
    async def calculate_quality_score(self, policy: Policy) -> float:
        """품질 점수 계산"""
        scores = []
        
        # 완성도 점수
        completeness = self.check_completeness(policy)
        scores.append(completeness * 0.4)
        
        # 정확도 점수
        accuracy = self.check_accuracy(policy)
        scores.append(accuracy * 0.3)
        
        # 최신성 점수
        freshness = self.check_freshness(policy)
        scores.append(freshness * 0.3)
        
        return sum(scores)
    
    def check_completeness(self, policy: Policy) -> float:
        """완성도 검사"""
        required_fields = [
            policy.title,
            policy.content,
            policy.issuing_organization,
            policy.category,
            policy.funding_type,
            policy.application_end_date
        ]
        
        filled = sum(1 for field in required_fields if field)
        return filled / len(required_fields)
    
    def check_accuracy(self, policy: Policy) -> float:
        """정확도 검사"""
        # 데이터 형식 검증, 논리적 일관성 등
        return 1.0  # 구현 필요
    
    def check_freshness(self, policy: Policy) -> float:
        """최신성 검사"""
        days_old = (datetime.utcnow() - policy.updated_at).days
        if days_old < 7:
            return 1.0
        elif days_old < 30:
            return 0.8
        elif days_old < 90:
            return 0.6
        else:
            return 0.4
```



## 5. Data Models

### 5.1 Database Models (SQLAlchemy)

```python
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum, Float, Boolean, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PyEnum

class PolicyStatus(str, PyEnum):
    """정책 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    DRAFT = "draft"
    ARCHIVED = "archived"

class Policy(Base):
    """정책 모델"""
    __tablename__ = "policies"
    
    # 기본 키
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 기본 정보
    title = Column(String(512), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    issuing_organization = Column(String(255), nullable=False, index=True)
    
    # 분류 정보
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    tags = Column(JSON, default=list)
    
    # 대상 정보
    target_regions = Column(JSON, default=list)
    target_industries = Column(JSON, default=list)
    target_business_types = Column(JSON, default=list)
    
    # 지원 정보
    funding_type = Column(String(50))
    min_funding_amount = Column(BigInteger)
    max_funding_amount = Column(BigInteger)
    interest_rate = Column(Float)
    
    # 신청 정보
    application_start_date = Column(DateTime)
    application_end_date = Column(DateTime)
    application_url = Column(String(512))
    application_method = Column(String(255))
    
    # 연락처 정보
    contact_department = Column(String(255))
    contact_phone = Column(String(50))
    contact_email = Column(String(255))
    
    # 메타데이터
    metadata = Column(JSON, default=dict)
    quality_score = Column(Float, default=0.0)
    
    # 상태 관리
    status = Column(Enum(PolicyStatus), default=PolicyStatus.ACTIVE, index=True)
    is_featured = Column(Boolean, default=False)
    
    # 원본 정보
    original_url = Column(String(512))
    source_system = Column(String(100), index=True)
    raw_data = Column(JSON)
    
    # 시스템 필드
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    
    # 인덱스
    __table_args__ = (
        Index('idx_policy_title', 'title'),
        Index('idx_policy_organization', 'issuing_organization'),
        Index('idx_policy_category', 'category'),
        Index('idx_policy_status', 'status'),
        Index('idx_policy_created_at', 'created_at'),
        Index('idx_policy_funding_amount', 'max_funding_amount'),
    )

class PolicyVersion(Base):
    """정책 버전 모델"""
    __tablename__ = "policy_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    
    # 버전 데이터 (JSON으로 저장)
    policy_data = Column(JSON, nullable=False)
    
    # 변경 정보
    changes = Column(JSON)
    changed_by = Column(String(255))
    change_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_version_policy_id', 'policy_id'),
        Index('idx_version_number', 'version_number'),
    )
```

### 5.2 API Request/Response Models (Pydantic)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class CreatePolicyRequest(BaseModel):
    """정책 생성 요청"""
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    issuing_organization: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    tags: List[str] = []
    target_regions: List[str] = []
    target_industries: List[str] = []
    funding_type: Optional[str] = None
    min_funding_amount: Optional[int] = Field(None, ge=0)
    max_funding_amount: Optional[int] = Field(None, ge=0)
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    application_start_date: Optional[datetime] = None
    application_end_date: Optional[datetime] = None
    application_url: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    @validator('max_funding_amount')
    def validate_funding_amount(cls, v, values):
        if v and 'min_funding_amount' in values:
            min_amount = values['min_funding_amount']
            if min_amount and v < min_amount:
                raise ValueError('max_funding_amount must be >= min_funding_amount')
        return v

class UpdatePolicyRequest(BaseModel):
    """정책 업데이트 요청"""
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    status: Optional[PolicyStatus] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)

class PolicyResponse(BaseModel):
    """정책 응답"""
    id: UUID
    title: str
    content: str
    issuing_organization: str
    category: Optional[str]
    subcategory: Optional[str]
    tags: List[str]
    target_regions: List[str]
    target_industries: List[str]
    funding_type: Optional[str]
    min_funding_amount: Optional[int]
    max_funding_amount: Optional[int]
    interest_rate: Optional[float]
    application_start_date: Optional[datetime]
    application_end_date: Optional[datetime]
    application_url: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    metadata: Dict[str, Any]
    quality_score: float
    status: PolicyStatus
    source_system: str
    created_at: datetime
    updated_at: datetime
    version: int
    
    class Config:
        from_attributes = True

class PaginatedPolicyResponse(BaseModel):
    """페이징된 정책 응답"""
    items: List[PolicyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(
        cls,
        items: List[PolicyResponse],
        total: int,
        page: int,
        page_size: int
    ):
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
```

### 5.3 Event Schemas (VersionedEvent)

```python
from aegis_shared.messaging import VersionedEvent
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class PolicyCreatedEvent(VersionedEvent):
    """정책 생성 이벤트"""
    event_type: str = "policy.created"
    version: str = "1.0.0"
    
    class Data(BaseModel):
        policy_id: UUID
        title: str
        organization: str
        category: Optional[str]
        source: str
        created_by: Optional[str]
        created_at: datetime

class PolicyUpdatedEvent(VersionedEvent):
    """정책 업데이트 이벤트"""
    event_type: str = "policy.updated"
    version: str = "1.0.0"
    
    class Data(BaseModel):
        policy_id: UUID
        title: str
        version: int
        changes: List[str]
        updated_by: Optional[str]
        updated_at: datetime

class PolicyDeletedEvent(VersionedEvent):
    """정책 삭제 이벤트"""
    event_type: str = "policy.deleted"
    version: str = "1.0.0"
    
    class Data(BaseModel):
        policy_id: UUID
        title: str
        deleted_by: Optional[str]
        deleted_at: datetime
```

---

## 6. Error Handling

### 6.1 중앙 에러 코드 사용

```python
from aegis_shared.errors import ErrorCode, ServiceException

# Policy Service 전용 에러 코드 (중앙 레지스트리에 등록됨)
class PolicyErrorCode(ErrorCode):
    # 정책 관련 (2000-2099)
    POLICY_NOT_FOUND = "POLICY_2001"
    POLICY_DUPLICATE = "POLICY_2002"
    POLICY_INVALID_STATUS = "POLICY_2003"
    POLICY_VERSION_CONFLICT = "POLICY_2004"
    
    # 메타데이터 관련 (2100-2199)
    METADATA_INVALID = "POLICY_2101"
    METADATA_GENERATION_FAILED = "POLICY_2102"
    
    # 품질 관련 (2200-2299)
    QUALITY_SCORE_INVALID = "POLICY_2201"
    QUALITY_CHECK_FAILED = "POLICY_2202"
```

### 6.2 에러 처리 전략

```python
from aegis_shared.errors import ServiceException
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class PolicyNotFoundException(ServiceException):
    """정책 없음 에러"""
    def __init__(self, policy_id: str):
        super().__init__(
            error_code=PolicyErrorCode.POLICY_NOT_FOUND,
            message=f"Policy not found: {policy_id}",
            details={"policy_id": policy_id},
            status_code=404
        )
        logger.error("policy_not_found", policy_id=policy_id)

class PolicyDuplicateException(ServiceException):
    """정책 중복 에러"""
    def __init__(self, existing_id: str):
        super().__init__(
            error_code=PolicyErrorCode.POLICY_DUPLICATE,
            message="Policy already exists",
            details={"existing_id": existing_id},
            status_code=409
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

### 6.3 에러 복구 전략

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from aegis_shared.errors import ServiceException

class PolicyService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def create_policy_with_retry(
        self,
        policy_data: CreatePolicyRequest
    ) -> Policy:
        """재시도 로직이 있는 정책 생성"""
        try:
            return await self.policy_repo.create(policy_data)
        except DatabaseError as e:
            logger.warning(
                "database_error_retry",
                attempt=e.attempt_number
            )
            raise
```

---

## 7. Service Integration

### 7.1 발행하는 이벤트

| 이벤트 타입 | Topic | 설명 | 구독 서비스 |
|------------|-------|------|------------|
| policy.created | policy-events | 정책 생성 | Search, Recommendation, Data Pipeline |
| policy.updated | policy-events | 정책 업데이트 | Search, Recommendation |
| policy.deleted | policy-events | 정책 삭제 | Search, Recommendation |
| policy.quality_changed | policy-events | 품질 점수 변경 | Data Pipeline |

### 7.2 구독하는 이벤트

| 이벤트 타입 | Topic | 발행 서비스 | 처리 내용 |
|------------|-------|------------|----------|
| policy.validated | data-pipeline-events | Data Pipeline | 검증된 정책 데이터 수신 및 저장 |
| policy.quality_updated | data-pipeline-events | Data Pipeline | 품질 점수 업데이트 |
| data.consistency_check | data-pipeline-events | Data Pipeline | 데이터 일관성 검증 및 수정 |

### 7.3 API 호출 관계

| 대상 서비스 | 엔드포인트 | 목적 | 필수/선택 |
|-----------|-----------|------|----------|
| User Service | GET /api/v1/users/{id} | 사용자 정보 조회 | 선택 |
| Search Service | POST /api/v1/index/policies | 검색 인덱스 업데이트 | 선택 |

### 7.4 데이터베이스 연결

| 데이터베이스 | 용도 | 연결 정보 |
|------------|------|----------|
| PostgreSQL | Source of Truth | postgresql://policy-db:5432/aegis_policy |
| Redis | 캐시 | redis://redis:6379/2 |
| Elasticsearch | 검색 인덱스 | http://elasticsearch:9200 |



## 8. Production Considerations

### 8.1 Scalability (확장성)

#### 8.1.1 Kubernetes HPA 설정

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: policy-service-hpa
  namespace: aegis
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: policy-service
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

#### 8.1.2 데이터베이스 연결 풀 관리

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

#### 8.1.3 부하 분산 전략

```yaml
apiVersion: v1
kind: Service
metadata:
  name: policy-service
  namespace: aegis
spec:
  type: ClusterIP
  sessionAffinity: None  # 무상태 설계로 세션 어피니티 불필요
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
  selector:
    app: policy-service
```

### 8.2 Fault Tolerance (장애 복구)

#### 8.2.1 Circuit Breaker 패턴

```python
from circuitbreaker import circuit
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class ExternalServiceClient:
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def call_search_service(self, data: dict):
        """Search Service 호출 (Circuit Breaker 적용)"""
        try:
            response = await self.http_client.post(
                "http://search-service/api/v1/index/policies",
                json=data
            )
            return response.json()
        except Exception as e:
            logger.error("search_service_call_failed", error=str(e))
            raise
```

#### 8.2.2 Retry 전략 (Tenacity)

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class PolicyService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseError),
        reraise=True
    )
    async def create_policy_with_retry(
        self,
        policy_data: CreatePolicyRequest
    ) -> Policy:
        """재시도 로직이 있는 정책 생성"""
        return await self.policy_repo.create(policy_data)
```

#### 8.2.3 Timeout 설정

```python
import asyncio
from fastapi import HTTPException

async def with_timeout(coro, timeout: float = 5.0):
    """타임아웃이 있는 비동기 작업"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout")

@router.post("/policies")
async def create_policy(request: CreatePolicyRequest):
    """타임아웃이 적용된 정책 생성"""
    return await with_timeout(
        policy_service.create_policy(request),
        timeout=10.0
    )
```

#### 8.2.4 Health Check 엔드포인트

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
        "redis": False,
        "kafka": False
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
    
    # Kafka 연결 확인
    try:
        # Kafka health check 로직
        checks["kafka"] = True
    except Exception as e:
        logger.error("kafka_health_check_failed", error=str(e))
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks}
        )
```

#### 8.2.5 Graceful Shutdown

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
        
        # Kafka 연결 종료
        await kafka_producer.stop()
        
        logger.info("shutdown_completed")
    
    def setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.shutdown()))
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.shutdown()))
```

### 8.3 Caching Strategy (캐싱 전략)

#### 8.3.1 다층 캐싱 (L1: 메모리, L2: Redis)

```python
from functools import lru_cache
from aegis_shared.cache import cache_result, RedisClient

class PolicyService:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
    
    @lru_cache(maxsize=1000)  # L1: 메모리 캐시
    @cache_result(ttl=300, key_prefix="policy")  # L2: Redis 캐시
    async def get_policy_by_id(self, policy_id: str) -> Policy:
        """정책 조회 (2단계 캐싱)"""
        policy = await self.policy_repo.find_by_id(policy_id)
        if not policy:
            raise PolicyNotFoundException(policy_id)
        return policy
```

#### 8.3.2 캐시 무효화 전략

```python
class PolicyService:
    async def update_policy(
        self,
        policy_id: str,
        data: UpdatePolicyRequest
    ) -> Policy:
        """정책 업데이트 (캐시 무효화)"""
        # 데이터베이스 업데이트
        policy = await self.policy_repo.update(policy_id, data)
        
        # 캐시 무효화
        await self.redis_client.delete(f"policy:{policy_id}")
        
        # 관련 캐시도 무효화
        await self.redis_client.delete(f"policy_list:*")
        
        # 이벤트 발행
        await self.event_publisher.publish(
            topic="policy-events",
            event_type="policy.updated",
            data={"policy_id": str(policy_id)}
        )
        
        return policy
```

#### 8.3.3 캐시 히트율 모니터링

```python
from prometheus_client import Counter, Histogram

cache_hits = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])

async def get_policy_with_metrics(policy_id: str) -> Policy:
    """캐시 히트율 메트릭이 있는 정책 조회"""
    # Redis 캐시 확인
    cached = await redis_client.get(f"policy:{policy_id}")
    if cached:
        cache_hits.labels(cache_type='redis').inc()
        return Policy.parse_raw(cached)
    
    cache_misses.labels(cache_type='redis').inc()
    
    # 데이터베이스 조회
    policy = await policy_repo.find_by_id(policy_id)
    
    # 캐시 저장
    await redis_client.setex(
        f"policy:{policy_id}",
        300,  # 5분 TTL
        policy.json()
    )
    
    return policy
```

### 8.4 Monitoring (모니터링)

#### 8.4.1 Prometheus 메트릭 상세

```python
from prometheus_client import Counter, Histogram, Gauge, Info

# 비즈니스 메트릭
policy_created_total = Counter(
    'policy_created_total',
    'Total policies created',
    ['source']  # 'manual', 'data_pipeline'
)

policy_updated_total = Counter(
    'policy_updated_total',
    'Total policies updated',
    ['source']
)

policy_deleted_total = Counter(
    'policy_deleted_total',
    'Total policies deleted'
)

policy_quality_score = Histogram(
    'policy_quality_score',
    'Policy quality score distribution',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# 성능 메트릭
policy_create_duration = Histogram(
    'policy_create_duration_seconds',
    'Policy creation duration in seconds',
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

policy_get_duration = Histogram(
    'policy_get_duration_seconds',
    'Policy retrieval duration in seconds',
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5]
)

# 시스템 메트릭
active_policies = Gauge(
    'policy_active_policies',
    'Number of active policies'
)

database_connections = Gauge(
    'policy_database_connections',
    'Number of active database connections'
)

# 서비스 정보
service_info = Info('policy_service', 'Policy service information')
service_info.info({
    'version': '1.0.0',
    'environment': 'production'
})
```

#### 8.4.2 Grafana 대시보드 설정

```json
{
  "dashboard": {
    "title": "Policy Service Dashboard",
    "panels": [
      {
        "title": "Policy Creation Rate",
        "targets": [
          {
            "expr": "rate(policy_created_total[5m])"
          }
        ]
      },
      {
        "title": "Policy Creation Duration (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(policy_create_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Policies",
        "targets": [
          {
            "expr": "policy_active_policies"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) * 100"
          }
        ]
      }
    ]
  }
}
```

#### 8.4.3 알림 조건 및 액션

```yaml
# Prometheus Alertmanager 규칙
groups:
- name: policy_service_alerts
  interval: 30s
  rules:
  # 높은 에러율
  - alert: HighPolicyCreationFailureRate
    expr: |
      rate(policy_created_total{status="failed"}[5m]) 
      / rate(policy_created_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
      service: policy-service
    annotations:
      summary: "High policy creation failure rate detected"
      description: "Policy creation failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
  
  # 느린 응답 시간
  - alert: SlowPolicyCreation
    expr: |
      histogram_quantile(0.95, 
        rate(policy_create_duration_seconds_bucket[5m])
      ) > 2
    for: 5m
    labels:
      severity: warning
      service: policy-service
    annotations:
      summary: "Slow policy creation detected"
      description: "95th percentile policy creation time is {{ $value }}s (threshold: 2s)"
  
  # 낮은 캐시 히트율
  - alert: LowCacheHitRate
    expr: |
      rate(cache_hits_total[5m]) 
      / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.7
    for: 10m
    labels:
      severity: info
      service: policy-service
    annotations:
      summary: "Low cache hit rate detected"
      description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 70%)"
  
  # 데이터베이스 연결 부족
  - alert: DatabaseConnectionPoolExhausted
    expr: policy_database_connections > 25
    for: 5m
    labels:
      severity: critical
      service: policy-service
    annotations:
      summary: "Database connection pool exhausted"
      description: "Database connections: {{ $value }} (max: 30)"
```

### 8.5 Security (보안)

#### 8.5.1 API 인증 및 권한 관리

```python
from aegis_shared.auth import require_role, get_current_user, JWTHandler

# JWT 토큰 검증
jwt_handler = JWTHandler()

@router.post("/policies")
@require_role(["admin", "moderator"])
async def create_policy(
    request: CreatePolicyRequest,
    current_user: dict = Depends(get_current_user)
):
    """정책 생성 (관리자/모더레이터만)"""
    return await policy_service.create_policy(request, current_user)
```

#### 8.5.2 Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.get("/policies")
@limiter.limit("100/minute")
async def list_policies(request: Request):
    """정책 목록 조회 (분당 100회 제한)"""
    return await policy_service.list_policies()
```

#### 8.5.3 데이터 암호화

```python
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """민감 데이터 암호화"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """민감 데이터 복호화"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```



## 9. Integration Testing Strategy

### 9.1 단위 테스트

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.policy_service import PolicyService
from app.models import Policy, PolicyStatus

class TestPolicyService:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            'policy_repo': AsyncMock(),
            'event_publisher': AsyncMock(),
            'metadata_service': AsyncMock(),
            'version_service': AsyncMock(),
            'quality_service': AsyncMock(),
            'redis_client': AsyncMock()
        }
    
    @pytest.fixture
    def policy_service(self, mock_dependencies):
        return PolicyService(**mock_dependencies)
    
    @pytest.mark.asyncio
    async def test_create_policy_success(
        self,
        policy_service,
        mock_dependencies
    ):
        # Given
        policy_data = CreatePolicyRequest(
            title="Test Policy",
            content="Test Content",
            issuing_organization="Test Org"
        )
        
        expected_policy = Policy(
            id=uuid.uuid4(),
            title=policy_data.title,
            content=policy_data.content,
            issuing_organization=policy_data.issuing_organization,
            status=PolicyStatus.ACTIVE
        )
        
        mock_dependencies['policy_repo'].create.return_value = expected_policy
        mock_dependencies['metadata_service'].generate_metadata.return_value = {}
        
        # When
        result = await policy_service.create_policy(
            policy_data,
            {'user_id': 'test-user'}
        )
        
        # Then
        assert result.id == expected_policy.id
        assert result.title == policy_data.title
        mock_dependencies['policy_repo'].create.assert_called_once()
        mock_dependencies['event_publisher'].publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_policy_duplicate_error(
        self,
        policy_service,
        mock_dependencies
    ):
        # Given
        policy_data = CreatePolicyRequest(
            title="Duplicate Policy",
            content="Test Content",
            issuing_organization="Test Org"
        )
        
        existing_policy = Policy(
            id=uuid.uuid4(),
            title=policy_data.title,
            issuing_organization=policy_data.issuing_organization
        )
        
        mock_dependencies['policy_repo'].find_by_title_and_org.return_value = [
            existing_policy
        ]
        
        # When/Then
        with pytest.raises(DuplicateEntityError):
            await policy_service.create_policy(
                policy_data,
                {'user_id': 'test-user'}
            )
```

### 9.2 통합 테스트

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
class TestPolicyAPI:
    async def test_create_and_get_policy(self):
        """정책 생성 및 조회 통합 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 정책 생성
            create_response = await client.post(
                "/api/v1/policies",
                json={
                    "title": "Integration Test Policy",
                    "content": "Test Content",
                    "issuing_organization": "Test Org",
                    "category": "창업지원"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert create_response.status_code == 201
            policy_data = create_response.json()
            policy_id = policy_data['id']
            
            # 정책 조회
            get_response = await client.get(
                f"/api/v1/policies/{policy_id}"
            )
            
            assert get_response.status_code == 200
            retrieved_policy = get_response.json()
            assert retrieved_policy['id'] == policy_id
            assert retrieved_policy['title'] == "Integration Test Policy"
    
    async def test_policy_lifecycle(self):
        """정책 생명주기 통합 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 생성
            create_response = await client.post(
                "/api/v1/policies",
                json={
                    "title": "Lifecycle Test Policy",
                    "content": "Original Content",
                    "issuing_organization": "Test Org"
                },
                headers={"Authorization": "Bearer admin-token"}
            )
            policy_id = create_response.json()['id']
            
            # 2. 수정
            update_response = await client.put(
                f"/api/v1/policies/{policy_id}",
                json={"content": "Updated Content"},
                headers={"Authorization": "Bearer admin-token"}
            )
            assert update_response.status_code == 200
            assert update_response.json()['content'] == "Updated Content"
            
            # 3. 삭제
            delete_response = await client.delete(
                f"/api/v1/policies/{policy_id}",
                headers={"Authorization": "Bearer admin-token"}
            )
            assert delete_response.status_code == 204
            
            # 4. 삭제 확인
            get_response = await client.get(
                f"/api/v1/policies/{policy_id}"
            )
            assert get_response.status_code == 404
```

### 9.3 이벤트 처리 테스트

```python
@pytest.mark.asyncio
class TestEventHandling:
    async def test_handle_policy_validated_event(self):
        """Data Pipeline 이벤트 처리 테스트"""
        # Given
        event = {
            'event_type': 'policy.validated',
            'data': {
                'title': 'Test Policy from Pipeline',
                'content': 'Test Content',
                'issuing_organization': 'Test Org',
                'source_system': 'data_pipeline',
                'quality_score': 0.85
            }
        }
        
        policy_service = AsyncMock()
        subscriber = PolicyEventSubscriber(
            'localhost:9092',
            policy_service
        )
        
        # When
        await subscriber.handle_policy_validated(event)
        
        # Then
        policy_service.create_from_pipeline.assert_called_once()
```

### 9.4 성능 테스트

```python
import pytest
import asyncio
from locust import HttpUser, task, between

class PolicyServiceUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_policy_list(self):
        """정책 목록 조회 (가중치 3)"""
        self.client.get("/api/v1/policies?limit=20")
    
    @task(2)
    def get_policy_detail(self):
        """정책 상세 조회 (가중치 2)"""
        policy_id = "test-policy-id"
        self.client.get(f"/api/v1/policies/{policy_id}")
    
    @task(1)
    def search_policies(self):
        """정책 검색 (가중치 1)"""
        self.client.get("/api/v1/policies/search?q=창업")

# 성능 테스트 실행
# locust -f test_performance.py --host=http://localhost:8000
```

---

## 10. Performance Benchmarks

### 10.1 응답 시간 목표

| 엔드포인트 | p50 | p95 | p99 | 최대 |
|-----------|-----|-----|-----|------|
| GET /policies/{id} | 50ms | 100ms | 200ms | 500ms |
| GET /policies | 100ms | 200ms | 500ms | 1s |
| POST /policies | 200ms | 500ms | 1s | 2s |
| PUT /policies/{id} | 150ms | 300ms | 800ms | 1.5s |
| DELETE /policies/{id} | 100ms | 200ms | 500ms | 1s |
| GET /policies/search | 200ms | 500ms | 1s | 3s |

### 10.2 처리량 (TPS) 목표

| 작업 | 목표 TPS | 최대 TPS |
|------|---------|---------|
| 정책 조회 | 1,000 | 2,000 |
| 정책 목록 | 500 | 1,000 |
| 정책 생성 | 100 | 200 |
| 정책 수정 | 100 | 200 |
| 정책 검색 | 200 | 500 |

### 10.3 리소스 제한

```yaml
resources:
  requests:
    cpu: "500m"      # 0.5 CPU
    memory: "512Mi"  # 512 MB
  limits:
    cpu: "2000m"     # 2 CPU
    memory: "2Gi"    # 2 GB
```

---

## 11. API Specification (OpenAPI 3.0)

```yaml
openapi: 3.0.3
info:
  title: Policy Service API
  version: 1.0.0
  description: 정책자금 정보 관리 API
  contact:
    name: Aegis Team
    email: team@aegis.com

servers:
  - url: https://api.aegis.com/policy/v1
    description: Production
  - url: https://staging-api.aegis.com/policy/v1
    description: Staging
  - url: http://localhost:8000/api/v1
    description: Development

paths:
  /policies:
    get:
      summary: 정책 목록 조회
      operationId: listPolicies
      tags: [Policies]
      parameters:
        - name: skip
          in: query
          schema:
            type: integer
            default: 0
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
            maximum: 1000
        - name: category
          in: query
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
            enum: [active, inactive, expired, draft, archived]
      responses:
        '200':
          description: 정책 목록
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedPolicyResponse'
    
    post:
      summary: 정책 생성
      operationId: createPolicy
      tags: [Policies]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreatePolicyRequest'
      responses:
        '201':
          description: 생성된 정책
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PolicyResponse'
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '409':
          $ref: '#/components/responses/ConflictError'

  /policies/{policyId}:
    get:
      summary: 정책 상세 조회
      operationId: getPolicy
      tags: [Policies]
      parameters:
        - name: policyId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: 정책 상세 정보
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PolicyResponse'
        '404':
          $ref: '#/components/responses/NotFoundError'
    
    put:
      summary: 정책 수정
      operationId: updatePolicy
      tags: [Policies]
      security:
        - bearerAuth: []
      parameters:
        - name: policyId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdatePolicyRequest'
      responses:
        '200':
          description: 수정된 정책
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PolicyResponse'
        '404':
          $ref: '#/components/responses/NotFoundError'
    
    delete:
      summary: 정책 삭제
      operationId: deletePolicy
      tags: [Policies]
      security:
        - bearerAuth: []
      parameters:
        - name: policyId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: 삭제 완료
        '404':
          $ref: '#/components/responses/NotFoundError'

  /policies/search:
    get:
      summary: 정책 검색
      operationId: searchPolicies
      tags: [Policies]
      parameters:
        - name: q
          in: query
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 200
        - name: category
          in: query
          schema:
            type: string
        - name: min_amount
          in: query
          schema:
            type: integer
        - name: max_amount
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: 검색 결과
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedPolicyResponse'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  
  schemas:
    PolicyResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        title:
          type: string
        content:
          type: string
        issuing_organization:
          type: string
        category:
          type: string
        status:
          type: string
          enum: [active, inactive, expired, draft, archived]
        quality_score:
          type: number
          format: float
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
    
    CreatePolicyRequest:
      type: object
      required:
        - title
        - content
        - issuing_organization
      properties:
        title:
          type: string
          minLength: 1
          maxLength: 512
        content:
          type: string
          minLength: 1
        issuing_organization:
          type: string
          minLength: 1
          maxLength: 255
        category:
          type: string
    
    UpdatePolicyRequest:
      type: object
      properties:
        title:
          type: string
        content:
          type: string
        status:
          type: string
          enum: [active, inactive, expired, draft, archived]
    
    PaginatedPolicyResponse:
      type: object
      properties:
        items:
          type: array
          items:
            $ref: '#/components/schemas/PolicyResponse'
        total:
          type: integer
        page:
          type: integer
        page_size:
          type: integer
        total_pages:
          type: integer
  
  responses:
    UnauthorizedError:
      description: 인증 실패
      content:
        application/json:
          schema:
            type: object
            properties:
              error_code:
                type: string
              message:
                type: string
    
    NotFoundError:
      description: 리소스를 찾을 수 없음
      content:
        application/json:
          schema:
            type: object
            properties:
              error_code:
                type: string
              message:
                type: string
    
    ConflictError:
      description: 리소스 충돌
      content:
        application/json:
          schema:
            type: object
            properties:
              error_code:
                type: string
              message:
                type: string
```



## 12. Database Schema

### 12.1 상세 스키마 정의

```sql
-- Policies Table
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 기본 정보
    title VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    issuing_organization VARCHAR(255) NOT NULL,
    
    -- 분류 정보
    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags JSONB DEFAULT '[]'::jsonb,
    
    -- 대상 정보
    target_regions JSONB DEFAULT '[]'::jsonb,
    target_industries JSONB DEFAULT '[]'::jsonb,
    target_business_types JSONB DEFAULT '[]'::jsonb,
    
    -- 지원 정보
    funding_type VARCHAR(50),
    min_funding_amount BIGINT,
    max_funding_amount BIGINT,
    interest_rate FLOAT,
    
    -- 신청 정보
    application_start_date TIMESTAMP WITH TIME ZONE,
    application_end_date TIMESTAMP WITH TIME ZONE,
    application_url VARCHAR(512),
    application_method VARCHAR(255),
    
    -- 연락처 정보
    contact_department VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(255),
    
    -- 메타데이터
    metadata JSONB DEFAULT '{}'::jsonb,
    quality_score FLOAT DEFAULT 0.0,
    
    -- 상태 관리
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'expired', 'draft', 'archived')),
    is_featured BOOLEAN DEFAULT FALSE,
    
    -- 원본 정보
    original_url VARCHAR(512),
    source_system VARCHAR(100),
    raw_data JSONB,
    
    -- 시스템 필드
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

-- 인덱스
CREATE INDEX idx_policies_title ON policies(title);
CREATE INDEX idx_policies_organization ON policies(issuing_organization);
CREATE INDEX idx_policies_category ON policies(category);
CREATE INDEX idx_policies_status ON policies(status);
CREATE INDEX idx_policies_created_at ON policies(created_at);
CREATE INDEX idx_policies_funding_amount ON policies(max_funding_amount);
CREATE INDEX idx_policies_source_system ON policies(source_system);

-- 전문 검색 인덱스 (PostgreSQL Full-Text Search)
CREATE INDEX idx_policies_title_fts ON policies USING gin(to_tsvector('korean', title));
CREATE INDEX idx_policies_content_fts ON policies USING gin(to_tsvector('korean', content));

-- JSONB 인덱스
CREATE INDEX idx_policies_tags_gin ON policies USING gin(tags);
CREATE INDEX idx_policies_target_regions_gin ON policies USING gin(target_regions);

-- Policy Versions Table
CREATE TABLE policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    policy_data JSONB NOT NULL,
    changes JSONB,
    changed_by VARCHAR(255),
    change_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE
);

CREATE INDEX idx_policy_versions_policy_id ON policy_versions(policy_id);
CREATE INDEX idx_policy_versions_version_number ON policy_versions(version_number);
CREATE UNIQUE INDEX idx_policy_versions_unique ON policy_versions(policy_id, version_number);

-- Updated At Trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_policies_updated_at
    BEFORE UPDATE ON policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 12.2 마이그레이션 전략

```python
# Alembic 마이그레이션 예시
"""create policies table

Revision ID: 001_initial
Revises: 
Create Date: 2025-10-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        # ... 나머지 컬럼
    )
    
    # 인덱스 생성
    op.create_index('idx_policies_title', 'policies', ['title'])
    op.create_index('idx_policies_organization', 'policies', ['issuing_organization'])

def downgrade():
    op.drop_table('policies')
```

---

## 13. Configuration Management

### 13.1 환경 변수

```bash
# .env.example
# Database Configuration
DATABASE_URL="postgresql://policy_user:password@localhost:5432/aegis_policy"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# Server Configuration
PORT=8000
NODE_ENV=development
API_VERSION=v1
CORS_ORIGINS="http://localhost:3000,http://localhost:3001"

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
KAFKA_CONSUMER_GROUP_ID="policy-service-consumer"
KAFKA_TOPICS="data-pipeline-events,policy-events"
KAFKA_AUTO_OFFSET_RESET="earliest"

# Redis Configuration
REDIS_URL="redis://localhost:6379/2"
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5

# Elasticsearch Configuration
ELASTICSEARCH_URL="http://localhost:9200"
ELASTICSEARCH_INDEX="policies"
ELASTICSEARCH_TIMEOUT=30

# Logging Configuration
LOG_LEVEL="info"
LOG_FORMAT="json"
LOG_FILE_PATH="./logs/policy-service.log"
LOG_MAX_SIZE="10m"
LOG_MAX_FILES=5

# Monitoring Configuration
METRICS_ENABLED=true
METRICS_PORT=9090
METRICS_PATH="/metrics"
HEALTH_CHECK_PATH="/health"

# Security Configuration
JWT_SECRET="your-jwt-secret"
JWT_ALGORITHM="HS256"
API_RATE_LIMIT=1000
API_RATE_WINDOW=900000

# Feature Flags
FEATURE_CACHE_ENABLED=true
FEATURE_METRICS_ENABLED=true
FEATURE_RATE_LIMITING=true
```

### 13.2 설정 클래스

```python
from pydantic import BaseSettings, Field
from typing import List

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
    # Server
    port: int = Field(8000, env="PORT")
    node_env: str = Field("development", env="NODE_ENV")
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    
    # Kafka
    kafka_bootstrap_servers: str = Field(..., env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group_id: str = Field(..., env="KAFKA_CONSUMER_GROUP_ID")
    kafka_topics: List[str] = Field(..., env="KAFKA_TOPICS")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    redis_max_connections: int = Field(50, env="REDIS_MAX_CONNECTIONS")
    
    # Elasticsearch
    elasticsearch_url: str = Field(..., env="ELASTICSEARCH_URL")
    elasticsearch_index: str = Field("policies", env="ELASTICSEARCH_INDEX")
    
    # Logging
    log_level: str = Field("info", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    # Security
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## 14. Logging Strategy

### 14.1 구조화된 로깅

```python
from aegis_shared.logging import get_logger, add_context
import structlog

# 로거 설정
logger = get_logger(__name__)

# 컨텍스트 추가
add_context(
    service="policy-service",
    version="1.0.0",
    environment="production"
)

# 로깅 예시
logger.info(
    "policy_created",
    policy_id=str(policy.id),
    title=policy.title,
    organization=policy.issuing_organization,
    created_by=user_id
)

logger.error(
    "policy_creation_failed",
    error=str(e),
    policy_data=policy_data.dict(),
    exc_info=True
)
```

### 14.2 로그 레벨 전략

| 레벨 | 용도 | 예시 |
|------|------|------|
| DEBUG | 개발 디버깅 | 상세한 변수 값, 쿼리 실행 |
| INFO | 정상 작업 | 정책 생성, 업데이트, 삭제 |
| WARNING | 주의 필요 | 캐시 미스, 재시도 발생 |
| ERROR | 에러 발생 | API 호출 실패, DB 에러 |
| CRITICAL | 심각한 에러 | 서비스 다운, 데이터 손실 |

### 14.3 로그 보관 정책

```yaml
# Filebeat 설정
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
    - add_kubernetes_metadata:
        host: ${NODE_NAME}

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "policy-service-logs-%{+yyyy.MM.dd}"

# ILM (Index Lifecycle Management)
setup.ilm.enabled: true
setup.ilm.rollover_alias: "policy-service-logs"
setup.ilm.pattern: "{now/d}-000001"
setup.ilm.policy_name: "policy-service-logs-policy"

# 보관 정책
# - Hot: 7일 (빠른 검색)
# - Warm: 30일 (압축 저장)
# - Cold: 90일 (아카이브)
# - Delete: 90일 후 삭제
```

---

## 15. Observability

### 15.1 분산 추적 (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Tracer 설정
tracer_provider = TracerProvider()
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent",
    agent_port=6831,
)
tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(tracer_provider)

# FastAPI 자동 계측
FastAPIInstrumentor.instrument_app(app)

# 커스텀 Span
tracer = trace.get_tracer(__name__)

@router.post("/policies")
async def create_policy(request: CreatePolicyRequest):
    with tracer.start_as_current_span("create_policy") as span:
        span.set_attribute("policy.title", request.title)
        span.set_attribute("policy.organization", request.issuing_organization)
        
        policy = await policy_service.create_policy(request)
        
        span.set_attribute("policy.id", str(policy.id))
        return policy
```

---

## 16. Disaster Recovery

### 16.1 백업 전략

```bash
# PostgreSQL 백업 (Cron Job)
0 2 * * * pg_dump -h postgres-primary -U policy_user -d aegis_policy \
  -F c -f /backups/policy_db_$(date +\%Y\%m\%d).dump

# S3 업로드
aws s3 cp /backups/policy_db_$(date +\%Y\%m\%d).dump \
  s3://aegis-backups/policy-service/
```

### 16.2 복구 절차

```bash
# 1. 전체 복구
pg_restore -h postgres-primary -U policy_user -d aegis_policy \
  -c /backups/policy_db_20251007.dump

# 2. 특정 시점 복구 (PITR)
recovery_target_time = '2025-10-07 14:30:00'
restore_command = 'cp /backups/wal/%f %p'
```

### 16.3 RTO/RPO 목표

| 항목 | 목표 | 설명 |
|------|------|------|
| RTO | < 1시간 | 서비스 복구까지 최대 시간 |
| RPO | < 5분 | 데이터 손실 허용 범위 |
| MTTR | < 30분 | 평균 복구 시간 |
| MTBF | > 720시간 | 평균 장애 간격 (30일) |

---

## 17. Dependency Management

### 17.1 Python 의존성

```txt
# requirements.txt
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Shared Library
aegis-shared==1.0.0

# Database
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.12.1

# Messaging
aiokafka==0.10.0

# Cache
redis==5.0.1
hiredis==2.2.3

# Search
elasticsearch==8.11.0

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
```

### 17.2 서비스 의존성 매트릭스

| 의존 서비스 | 통신 방식 | 목적 | 필수/선택 |
|-----------|----------|------|----------|
| Data Pipeline | Kafka (이벤트 구독) | 검증된 정책 데이터 수신 | 필수 |
| User Service | API 호출 | 사용자 정보 조회 | 선택 |
| Search Service | API 호출 | 검색 인덱스 업데이트 | 선택 |

---

## 18. Development Workflow

### 18.1 로컬 개발 환경

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  policy-service:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://policy_user:password@postgres:5432/aegis_policy
      - REDIS_URL=redis://redis:6379/2
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    volumes:
      - ./app:/app/app
      - ./tests:/app/tests
    depends_on:
      - postgres
      - redis
      - kafka
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=policy_user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=aegis_policy
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
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092

volumes:
  postgres_data:
```

---

## 19. Capacity Planning

### 19.1 예상 부하

| 메트릭 | 초기 | 6개월 | 1년 |
|--------|------|-------|-----|
| 정책 데이터 수 | 10,000 | 50,000 | 100,000 |
| 일일 조회 수 | 100,000 | 500,000 | 1,000,000 |
| 조회 TPS | 10 | 50 | 100 |
| 생성/수정 TPS | 1 | 5 | 10 |
| 데이터베이스 크기 | 1 GB | 5 GB | 10 GB |

### 19.2 리소스 계획

**Phase 1: 초기 (0-3개월)**
- Pod 수: 3개
- CPU: 1.5 cores (0.5 × 3)
- Memory: 1.5 GB (512 MB × 3)
- 예상 비용: $50/월

**Phase 2: 성장 (3-6개월)**
- Pod 수: 5-10개 (HPA)
- CPU: 2.5-5 cores
- Memory: 2.5-5 GB
- 예상 비용: $100-200/월

**Phase 3: 확장 (6-12개월)**
- Pod 수: 10-20개 (HPA)
- CPU: 5-10 cores
- Memory: 5-10 GB
- 예상 비용: $200-400/월

---

**문서 버전**: 2.0.0  
**최종 업데이트**: 2025-10-07  
**작성자**: Kiro AI  
**검토자**: -  
**승인자**: -



