# 정책 서비스 명세서 (Policy Service Specification)

| 항목 | 내용 |
|------|------|
| 문서 ID | AAS-POL-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 서비스 개요 (Service Overview)

정책 서비스는 이지스 시스템의 데이터 관리 중추로서, 정책자금 정보의 수집, 정제, 저장, 관리를 담당한다. 본 서비스는 **이중 트랙 파이프라인(Dual-Track Pipeline)**을 통해 데이터 무결성을 보장하며, 다양한 외부 데이터 소스로부터 정책 정보를 안정적으로 수집하고 표준화하여 시스템 전체에 제공한다.

### 1.1. 핵심 책임 (Core Responsibilities)
- 외부 정책 데이터 소스 연동 및 수집
- 정책 데이터 정제, 표준화, 검증
- 정책 메타데이터 관리 및 분류
- 정책 생명주기 관리 (생성, 수정, 만료, 삭제)
- 데이터 품질 모니터링 및 이상 탐지

### 1.2. 서비스 경계 (Service Boundaries)
**포함하는 기능:**
- 정책 데이터 CRUD 연산
- 외부 API 연동 및 데이터 수집
- 데이터 검증 및 품질 관리
- 정책 분류 및 태깅
- 변경 이력 추적

**포함하지 않는 기능:**
- 정책 추천 로직 (Recommendation Service 담당)
- 사용자 관리 (User Service 담당)
- 벡터 임베딩 생성 (Data Pipeline 담당)

## 2. 아키텍처 설계 (Architecture Design)

### 2.1. 서비스 구조
```
┌─────────────────────────────────────────────────────────────┐
│                    Policy Service                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Data Collector  │  │ Data Processor  │  │ Data Manager │ │
│  │                 │  │                 │  │              │ │
│  │ - API Clients   │  │ - Validation    │  │ - CRUD Ops   │ │
│  │ - Web Scrapers  │  │ - Normalization │  │ - Lifecycle  │ │
│  │ - File Parsers  │  │ - Classification│  │ - Versioning │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Quality Monitor │  │ Change Tracker  │  │ Cache Layer  │ │
│  │                 │  │                 │  │              │ │
│  │ - Data Quality  │  │ - Audit Trail   │  │ - Query      │ │
│  │ - Anomaly Detect│  │ - Event Stream  │  │ - Metadata   │ │
│  │ - Health Check  │  │ - CDC Events    │  │ - Statistics │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. 데이터 흐름 (Data Flow)
```
[External Sources] → [Data Collector] → [Data Processor] → [Data Manager] → [PostgreSQL]
        ↓                  ↓                 ↓                ↓              ↓
[API/Scraper] → [Raw Data Queue] → [Validation] → [Normalization] → [CDC Events]
        ↓                  ↓                 ↓                ↓              ↓
[Quality Check] ← [Quality Monitor] ← [Change Tracker] ← [Event Stream] → [Kafka]
```

## 3. 핵심 컴포넌트 상세 (Core Components)

### 3.1. Data Collector (데이터 수집기)
다양한 외부 소스로부터 정책 데이터를 수집한다.

**지원 데이터 소스:**
- **공공데이터포털 API**: 정부 정책자금 정보
- **지자체 웹사이트**: 지역별 지원 정책
- **금융기관 API**: 보증서 및 대출 상품
- **RSS/XML 피드**: 정책 업데이트 알림

**수집 전략:**
```python
class DataCollector:
    async def collect_from_source(self, source_config: SourceConfig) -> List[RawPolicy]:
        """데이터 소스별 맞춤형 수집 로직"""
        if source_config.type == "api":
            return await self._collect_from_api(source_config)
        elif source_config.type == "scraper":
            return await self._collect_from_web(source_config)
        elif source_config.type == "file":
            return await self._collect_from_file(source_config)
    
    async def _collect_from_api(self, config: APISourceConfig) -> List[RawPolicy]:
        """API 기반 데이터 수집"""
        async with aiohttp.ClientSession() as session:
            # 페이지네이션 처리
            all_policies = []
            page = 1
            while True:
                response = await session.get(
                    config.endpoint,
                    params={**config.params, "page": page},
                    headers=config.headers
                )
                
                if response.status != 200:
                    break
                    
                data = await response.json()
                policies = self._parse_api_response(data, config.schema)
                
                if not policies:
                    break
                    
                all_policies.extend(policies)
                page += 1
                
                # 요청 제한 준수
                await asyncio.sleep(config.rate_limit_delay)
            
            return all_policies
```

### 3.2. Data Processor (데이터 처리기)
수집된 원시 데이터를 검증, 정제, 표준화한다.

**처리 단계:**
1. **스키마 검증**: 필수 필드 존재 여부 확인
2. **데이터 정제**: 중복 제거, 형식 통일
3. **분류 및 태깅**: 자동 카테고리 분류
4. **품질 점수 계산**: 데이터 완성도 평가

```python
class DataProcessor:
    async def process_raw_policy(self, raw_policy: RawPolicy) -> ProcessedPolicy:
        """원시 정책 데이터 처리"""
        # 1. 스키마 검증
        validation_result = await self.validator.validate(raw_policy)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        
        # 2. 데이터 정제
        cleaned_data = await self.cleaner.clean(raw_policy)
        
        # 3. 자동 분류
        classification = await self.classifier.classify(cleaned_data)
        
        # 4. 메타데이터 생성
        metadata = await self._generate_metadata(cleaned_data, classification)
        
        return ProcessedPolicy(
            original_data=raw_policy,
            cleaned_data=cleaned_data,
            classification=classification,
            metadata=metadata,
            quality_score=self._calculate_quality_score(cleaned_data)
        )
    
    def _calculate_quality_score(self, data: CleanedPolicy) -> float:
        """데이터 품질 점수 계산"""
        score = 0.0
        total_weight = 0.0
        
        # 필수 필드 완성도 (가중치: 0.4)
        required_fields = ["title", "organization", "content", "eligibility"]
        required_completeness = sum(1 for field in required_fields if getattr(data, field)) / len(required_fields)
        score += required_completeness * 0.4
        total_weight += 0.4
        
        # 선택 필드 완성도 (가중치: 0.2)
        optional_fields = ["contact_info", "application_url", "deadline"]
        optional_completeness = sum(1 for field in optional_fields if getattr(data, field)) / len(optional_fields)
        score += optional_completeness * 0.2
        total_weight += 0.2
        
        # 내용 품질 (가중치: 0.4)
        content_quality = self._assess_content_quality(data.content)
        score += content_quality * 0.4
        total_weight += 0.4
        
        return score / total_weight if total_weight > 0 else 0.0
```

### 3.3. Data Manager (데이터 관리자)
정책 데이터의 생명주기를 관리한다.

**주요 기능:**
- **CRUD 연산**: 정책 생성, 조회, 수정, 삭제
- **버전 관리**: 정책 변경 이력 추적
- **상태 관리**: 활성/비활성/만료 상태 관리
- **관계 관리**: 정책 간 연관 관계 설정

```python
class DataManager:
    async def create_policy(self, processed_policy: ProcessedPolicy) -> Policy:
        """새 정책 생성"""
        async with self.db.transaction():
            # 중복 검사
            existing = await self._find_duplicate(processed_policy)
            if existing:
                return await self._update_existing_policy(existing, processed_policy)
            
            # 새 정책 생성
            policy = Policy(
                id=uuid4(),
                title=processed_policy.title,
                content=processed_policy.content,
                metadata=processed_policy.metadata,
                quality_score=processed_policy.quality_score,
                status=PolicyStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            
            await self.db.save(policy)
            
            # 변경 이벤트 발행
            await self.event_publisher.publish(PolicyCreatedEvent(policy_id=policy.id))
            
            return policy
    
    async def update_policy(self, policy_id: UUID, updates: PolicyUpdate) -> Policy:
        """정책 업데이트"""
        async with self.db.transaction():
            policy = await self.db.get(Policy, policy_id)
            if not policy:
                raise PolicyNotFoundError(policy_id)
            
            # 변경 이력 저장
            change_record = PolicyChangeRecord(
                policy_id=policy_id,
                changes=updates.dict(exclude_unset=True),
                changed_by="system",
                changed_at=datetime.utcnow()
            )
            await self.db.save(change_record)
            
            # 정책 업데이트
            for field, value in updates.dict(exclude_unset=True).items():
                setattr(policy, field, value)
            
            policy.updated_at = datetime.utcnow()
            await self.db.save(policy)
            
            # 변경 이벤트 발행
            await self.event_publisher.publish(PolicyUpdatedEvent(
                policy_id=policy_id,
                changes=updates.dict(exclude_unset=True)
            ))
            
            return policy
```

## 4. API 명세 (API Specification)

### 4.1. 정책 조회 API
```http
GET /api/v1/policies/{policy_id}
Authorization: Bearer {jwt_token}
```

**응답 예시:**
```json
{
    "success": true,
    "data": {
        "policy_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "title": "경기도 소상공인 특별경영자금",
        "issuing_organization": "경기도청",
        "content": "상세 내용...",
        "metadata": {
            "category": "운영자금",
            "target_regions": ["경기도"],
            "target_industries": ["전업종"],
            "funding_range": [5000000, 50000000]
        },
        "quality_score": 0.95,
        "status": "active",
        "created_at": "2025-09-17T10:30:00Z",
        "updated_at": "2025-09-17T10:30:00Z"
    }
}
```

### 4.2. 정책 검색 API
```http
GET /api/v1/policies/search?q=창업자금&region=서울&limit=20
Authorization: Bearer {jwt_token}
```

### 4.3. 정책 생성 API (관리자 전용)
```http
POST /api/v1/policies
Authorization: Bearer {admin_jwt_token}
Content-Type: application/json

{
    "title": "새로운 정책명",
    "issuing_organization": "발행기관",
    "content": "정책 내용...",
    "metadata": { ... }
}
```

### 4.4. 데이터 수집 트리거 API (관리자 전용)
```http
POST /api/v1/policies/collect
Authorization: Bearer {admin_jwt_token}
Content-Type: application/json

{
    "source_ids": ["source_1", "source_2"],
    "force_refresh": false
}
```

## 5. 데이터 모델 (Data Models)

### 5.1. 정책 모델
```python
class Policy(BaseModel):
    policy_id: UUID
    title: str = Field(..., min_length=1, max_length=512)
    issuing_organization: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # 대상 정보
    target_regions: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    target_business_types: List[str] = Field(default_factory=list)
    
    # 자금 정보
    funding_details: Optional[FundingDetails] = None
    
    # 신청 정보
    application_start_date: Optional[date] = None
    application_end_date: Optional[date] = None
    application_url: Optional[str] = None
    
    # 품질 및 상태
    quality_score: float = Field(..., ge=0, le=1)
    status: PolicyStatus = PolicyStatus.ACTIVE
    
    # 원본 정보
    original_url: Optional[str] = None
    source_system: Optional[str] = None
    
    # 시스템 필드
    created_at: datetime
    updated_at: datetime

class FundingDetails(BaseModel):
    funding_type: str  # "대출", "보조금", "융자" 등
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    interest_rate: Optional[float] = None
    repayment_period: Optional[str] = None
    guarantee_required: Optional[bool] = None

class PolicyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    DRAFT = "draft"
```

### 5.2. 데이터 소스 설정 모델
```python
class DataSourceConfig(BaseModel):
    source_id: str
    name: str
    type: SourceType
    config: Dict[str, Any]
    schedule: str  # Cron expression
    is_active: bool = True
    
class SourceType(str, Enum):
    API = "api"
    WEB_SCRAPER = "scraper"
    FILE = "file"
    RSS = "rss"

class APISourceConfig(BaseModel):
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    auth: Optional[Dict[str, str]] = None
    rate_limit_delay: float = 1.0
    schema_mapping: Dict[str, str]
```

## 6. 데이터 품질 관리 (Data Quality Management)

### 6.1. 품질 메트릭
```python
class QualityMetrics:
    def __init__(self):
        self.completeness_score = Gauge('policy_data_completeness')
        self.accuracy_score = Gauge('policy_data_accuracy')
        self.freshness_score = Gauge('policy_data_freshness')
        self.consistency_score = Gauge('policy_data_consistency')
    
    async def calculate_completeness(self, policy: Policy) -> float:
        """데이터 완성도 계산"""
        required_fields = ["title", "content", "issuing_organization"]
        optional_fields = ["summary", "application_url", "contact_info"]
        
        required_score = sum(1 for field in required_fields if getattr(policy, field)) / len(required_fields)
        optional_score = sum(1 for field in optional_fields if getattr(policy, field)) / len(optional_fields)
        
        return (required_score * 0.7) + (optional_score * 0.3)
    
    async def calculate_freshness(self, policy: Policy) -> float:
        """데이터 신선도 계산"""
        now = datetime.utcnow()
        age_days = (now - policy.updated_at).days
        
        # 30일 이내: 1.0, 90일 이후: 0.0
        if age_days <= 30:
            return 1.0
        elif age_days >= 90:
            return 0.0
        else:
            return 1.0 - ((age_days - 30) / 60)
```

### 6.2. 이상 탐지
```python
class AnomalyDetector:
    async def detect_anomalies(self, policies: List[Policy]) -> List[Anomaly]:
        """데이터 이상 탐지"""
        anomalies = []
        
        # 중복 탐지
        duplicates = await self._detect_duplicates(policies)
        anomalies.extend(duplicates)
        
        # 품질 저하 탐지
        quality_issues = await self._detect_quality_issues(policies)
        anomalies.extend(quality_issues)
        
        # 일관성 문제 탐지
        consistency_issues = await self._detect_consistency_issues(policies)
        anomalies.extend(consistency_issues)
        
        return anomalies
    
    async def _detect_duplicates(self, policies: List[Policy]) -> List[DuplicateAnomaly]:
        """중복 정책 탐지"""
        duplicates = []
        seen_titles = {}
        
        for policy in policies:
            normalized_title = self._normalize_title(policy.title)
            if normalized_title in seen_titles:
                duplicates.append(DuplicateAnomaly(
                    policy_id=policy.policy_id,
                    duplicate_of=seen_titles[normalized_title],
                    similarity_score=self._calculate_similarity(
                        policy, seen_titles[normalized_title]
                    )
                ))
            else:
                seen_titles[normalized_title] = policy
        
        return duplicates
```

## 7. 성능 요구사항 (Performance Requirements)

### 7.1. 처리량 목표
- **정책 조회**: 10,000 QPS
- **정책 검색**: 1,000 QPS  
- **데이터 수집**: 1,000 정책/분
- **데이터 처리**: 500 정책/분

### 7.2. 응답 시간 목표
- **단일 정책 조회**: 100ms 이내
- **정책 검색**: 500ms 이내
- **정책 생성/수정**: 1초 이내

### 7.3. 가용성 목표
- **서비스 가용성**: 99.9%
- **데이터 일관성**: 99.99%
- **백업 복구**: RTO 4시간, RPO 1시간

## 8. 모니터링 및 알림 (Monitoring & Alerting)

### 8.1. 핵심 메트릭
```python
# 비즈니스 메트릭
total_policies = Gauge('total_policies_count')
active_policies = Gauge('active_policies_count')
data_quality_score = Gauge('overall_data_quality_score')

# 수집 메트릭
collection_success_rate = Gauge('data_collection_success_rate')
collection_latency = Histogram('data_collection_latency_seconds')
processing_queue_size = Gauge('data_processing_queue_size')

# 에러 메트릭
collection_errors = Counter('data_collection_errors_total')
processing_errors = Counter('data_processing_errors_total')
validation_failures = Counter('data_validation_failures_total')
```

### 8.2. 알림 규칙
- **데이터 수집 실패율 > 10%**: 즉시 알림
- **처리 대기열 크기 > 1000**: 경고 알림
- **데이터 품질 점수 < 0.8**: 일일 리포트
- **신규 정책 0개 > 24시간**: 경고 알림

## 9. 보안 고려사항 (Security Considerations)

### 9.1. 데이터 보호
- 외부 API 키 암호화 저장
- 수집된 데이터 무결성 검증
- 민감 정보 마스킹 처리

### 9.2. 접근 제어
- 관리자 전용 API 별도 인증
- 데이터 소스별 접근 권한 관리
- 감사 로그 기록

---

**📋 관련 문서**
- [이중 트랙 파이프라인](../../02_CORE_COMPONENTS/01_DUAL_TRACK_PIPELINE.md)
- [데이터베이스 스키마](../../03_DATA_MODELS_AND_APIS/DATABASE_SCHEMA.md)
- [API 명세서](../../03_DATA_MODELS_AND_APIS/API_CONTRACT.md)