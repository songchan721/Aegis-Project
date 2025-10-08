# 이지스(Aegis) 설계 가이드라인
**개발팀을 위한 기술 설계 원칙 및 표준**

| 항목 | 내용 |
|------|------|
| 문서 ID | ADG-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 설계 철학 (Design Philosophy)

### 1.1. 핵심 원칙: S.C.O.R.E. 프레임워크
모든 코드와 시스템 설계는 **S.C.O.R.E. 프레임워크**를 준수해야 합니다.

- **S**pecificity (구체성): 모든 함수와 클래스는 명확한 단일 책임을 가져야 함
- **C**onsistency (일관성): 동일한 입력에 대해 항상 동일한 결과를 보장해야 함
- **O**bservability (관찰가능성): 모든 중요한 처리 과정을 로깅하고 추적 가능해야 함
- **R**eproducibility (재현가능성): 모든 결과를 재현할 수 있는 환경을 제공해야 함
- **E**xplainability (설명가능성): 모든 AI 판단의 근거를 명확히 제시해야 함

### 1.2. 언어 지능 계층(LIL) 설계 원칙
외부 LLM을 시스템의 '부품'으로 완전히 제어하기 위한 설계 원칙:

```python
# ❌ 잘못된 예: LLM에 직접 의존
def get_recommendation(query: str) -> str:
    return openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}]
    ).choices[0].message.content

# ✅ 올바른 예: LIL을 통한 제어
def get_recommendation(query: str) -> RecommendationResult:
    processed_query = self.lil.parse_user_intent(query)
    raw_response = self.lil.generate_response(processed_query)
    validated_result = self.lil.validate_and_structure(raw_response)
    return validated_result
```

## 2. 코드 구조 및 아키텍처 패턴

### 2.1. 디렉토리 구조 표준
```
backend/
├── app/
│   ├── core/                    # 핵심 설정 및 공통 유틸리티
│   │   ├── config.py           # 환경 설정
│   │   ├── security.py         # 인증/보안
│   │   ├── database.py         # DB 연결 관리
│   │   └── logging.py          # 로깅 설정
│   ├── models/                  # 데이터 모델 (Pydantic/SQLAlchemy)
│   │   ├── domain/             # 도메인 모델
│   │   ├── database/           # DB 모델
│   │   └── api/                # API 요청/응답 모델
│   ├── services/               # 비즈니스 로직
│   │   ├── recommendation/     # 추천 서비스
│   │   ├── search/             # 검색 서비스
│   │   ├── user/               # 사용자 관리
│   │   └── lil/                # 언어 지능 계층
│   ├── repositories/           # 데이터 접근 계층
│   │   ├── policy_repository.py
│   │   ├── user_repository.py
│   │   └── vector_repository.py
│   ├── api/                    # API 라우터
│   │   ├── v1/
│   │   │   ├── recommendations.py
│   │   │   ├── policies.py
│   │   │   └── auth.py
│   │   └── dependencies.py     # 의존성 주입
│   └── utils/                  # 유틸리티 함수
├── tests/                      # 테스트 코드
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── migrations/                 # DB 마이그레이션
```

### 2.2. 계층별 책임 분리

#### Repository Pattern (데이터 접근 계층)
```python
from abc import ABC, abstractmethod
from typing import List, Optional

class PolicyRepository(ABC):
    @abstractmethod
    async def find_by_id(self, policy_id: str) -> Optional[Policy]:
        pass
    
    @abstractmethod
    async def search_by_criteria(self, criteria: SearchCriteria) -> List[Policy]:
        pass

class PostgreSQLPolicyRepository(PolicyRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def find_by_id(self, policy_id: str) -> Optional[Policy]:
        # PostgreSQL 구현
        pass
```

#### Service Pattern (비즈니스 로직 계층)
```python
class RecommendationService:
    def __init__(
        self,
        policy_repo: PolicyRepository,
        vector_search: VectorSearchService,
        knowledge_graph: KnowledgeGraphService,
        lil: LanguageIntelligenceLayer
    ):
        self.policy_repo = policy_repo
        self.vector_search = vector_search
        self.kg = knowledge_graph
        self.lil = lil
    
    async def get_recommendations(
        self, 
        query: str, 
        user_profile: UserProfile
    ) -> RecommendationResult:
        # S.C.O.R.E. 프레임워크 적용
        with self.observability.trace("recommendation_process"):
            # 1. Specificity: 명확한 단계별 처리
            parsed_query = await self.lil.parse_user_intent(query)
            
            # 2. Consistency: 동일한 로직으로 처리
            candidates = await self.vector_search.find_similar(parsed_query)
            
            # 3. Observability: 각 단계 로깅
            self.logger.info(f"Found {len(candidates)} candidates")
            
            # 4. Reproducibility: 결정적 알고리즘 사용
            scored_results = await self.kg.score_and_rank(candidates, user_profile)
            
            # 5. Explainability: 추천 근거 생성
            explanations = await self.generate_explanations(scored_results)
            
            return RecommendationResult(
                recommendations=scored_results,
                explanations=explanations,
                metadata=self.get_processing_metadata()
            )
```

## 3. 데이터 모델링 가이드라인

### 3.1. Pydantic 모델 설계
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class BusinessType(str, Enum):
    SMALL_BUSINESS = "소상공인"
    SME = "중소기업"
    INDIVIDUAL = "개인사업자"

class UserProfile(BaseModel):
    """사용자 프로필 모델 - AI 추천에 사용되는 핵심 정보"""
    
    business_info: BusinessInfo = Field(..., description="사업체 정보")
    location: LocationInfo = Field(..., description="위치 정보")
    financial_info: Optional[FinancialInfo] = Field(None, description="재무 정보")
    
    class Config:
        # JSON 스키마 생성 시 예시 포함
        schema_extra = {
            "example": {
                "business_info": {
                    "business_type": "소상공인",
                    "industry_code": "56",
                    "establishment_date": "2025-06-15"
                }
            }
        }
    
    @validator('business_info')
    def validate_business_info(cls, v):
        if not v.industry_code:
            raise ValueError('업종 코드는 필수입니다')
        return v
```

### 3.2. SQLAlchemy 모델 설계
```python
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Policy(Base):
    __tablename__ = "policies"
    
    # 기본 키
    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 필수 필드
    title = Column(String(512), nullable=False, index=True)
    issuing_organization = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=False)
    
    # 메타데이터 (유연성을 위한 JSONB)
    metadata = Column(JSONB, nullable=False, default={})
    
    # 시스템 필드
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 인덱스 최적화
    __table_args__ = (
        Index('idx_policy_active_title', 'is_active', 'title'),
        Index('idx_policy_metadata_gin', 'metadata', postgresql_using='gin'),
    )
```

## 4. API 설계 가이드라인

### 4.1. FastAPI 라우터 구조
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import List

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])
security = HTTPBearer()

@router.post("/", response_model=RecommendationResponse)
async def create_recommendation(
    request: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
) -> RecommendationResponse:
    """
    정책자금 추천 생성
    
    - **query**: 사용자의 자연어 질문
    - **user_profile**: 사용자 프로필 정보
    - **search_options**: 검색 옵션 (선택사항)
    
    Returns:
        추천 결과 목록과 각 추천의 근거
    """
    try:
        # 입력 검증
        if not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="검색 쿼리는 필수입니다."
            )
        
        # 비즈니스 로직 실행
        result = await recommendation_service.get_recommendations(
            query=request.query,
            user_profile=request.user_profile,
            options=request.search_options
        )
        
        # 응답 변환
        return RecommendationResponse.from_domain(result)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"입력 데이터 검증 실패: {e}"
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="추천 서비스가 일시적으로 사용할 수 없습니다."
        )
```

### 4.2. 에러 처리 표준
```python
from enum import Enum
from typing import Optional, Dict, Any

class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"

class APIError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

# 전역 에러 핸들러
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": false,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.state.request_id
            }
        }
    )
```

## 5. 테스트 가이드라인

### 5.1. 단위 테스트 표준
```python
import pytest
from unittest.mock import AsyncMock, Mock
from app.services.recommendation import RecommendationService

class TestRecommendationService:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            'policy_repo': AsyncMock(),
            'vector_search': AsyncMock(),
            'knowledge_graph': AsyncMock(),
            'lil': AsyncMock()
        }
    
    @pytest.fixture
    def service(self, mock_dependencies):
        return RecommendationService(**mock_dependencies)
    
    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, service, mock_dependencies):
        # Given
        query = "창업자금 지원 정책"
        user_profile = UserProfile(...)
        
        mock_dependencies['vector_search'].find_similar.return_value = [
            Policy(policy_id="test-1", title="창업지원금")
        ]
        
        # When
        result = await service.get_recommendations(query, user_profile)
        
        # Then
        assert len(result.recommendations) > 0
        assert result.recommendations[0].policy.title == "창업지원금"
        
        # 의존성 호출 검증
        mock_dependencies['lil'].parse_user_intent.assert_called_once_with(query)
```

### 5.2. 통합 테스트 표준
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.integration
class TestRecommendationAPI:
    @pytest.mark.asyncio
    async def test_create_recommendation_e2e(self, test_client: AsyncClient):
        # Given
        request_data = {
            "query": "경기도 소상공인 운영자금",
            "user_profile": {
                "business_info": {
                    "business_type": "소상공인",
                    "industry_code": "56"
                },
                "location": {
                    "region_code": "41"
                }
            }
        }
        
        # When
        response = await test_client.post(
            "/api/v1/recommendations/",
            json=request_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["recommendations"]) > 0
        
        # S.C.O.R.E. 프레임워크 검증
        recommendation = data["data"]["recommendations"][0]
        assert "score_breakdown" in recommendation
        assert "explanation" in recommendation
```

## 6. 성능 및 최적화 가이드라인

### 6.1. 데이터베이스 최적화
```python
# ✅ 올바른 예: 인덱스 활용한 쿼리
async def find_policies_by_region_and_industry(
    self, 
    region_code: str, 
    industry_code: str
) -> List[Policy]:
    query = select(Policy).where(
        and_(
            Policy.is_active == True,
            Policy.metadata['target_regions'].astext.contains(region_code),
            Policy.metadata['target_industries'].astext.contains(industry_code)
        )
    ).options(
        # 필요한 필드만 로드
        load_only(Policy.policy_id, Policy.title, Policy.summary)
    )
    
    result = await self.db.execute(query)
    return result.scalars().all()

# ❌ 잘못된 예: N+1 쿼리 문제
async def get_recommendations_with_details(self, policy_ids: List[str]):
    recommendations = []
    for policy_id in policy_ids:  # N+1 쿼리 발생
        policy = await self.policy_repo.find_by_id(policy_id)
        recommendations.append(policy)
    return recommendations
```

### 6.2. 캐싱 전략
```python
from functools import wraps
import hashlib
import json

def cache_result(ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"aegis:{func.__name__}:{hash_args(args, kwargs)}"
            
            # 캐시 확인
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 실제 함수 실행
            result = await func(*args, **kwargs)
            
            # 캐시 저장
            await redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator

class RecommendationService:
    @cache_result(ttl=1800)  # 30분 캐시
    async def get_recommendations(self, query: str, user_profile: UserProfile):
        # 추천 로직 실행
        pass
```

## 7. 보안 가이드라인

### 7.1. 입력 검증 및 살균
```python
from pydantic import validator, Field
import re

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    
    @validator('query')
    def sanitize_query(cls, v):
        # SQL 인젝션 방지
        dangerous_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)',
            r'(script|javascript|vbscript)',
            r'(<|>|&lt;|&gt;)'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v.lower()):
                raise ValueError('허용되지 않는 문자가 포함되어 있습니다.')
        
        return v.strip()
```

### 7.2. 민감 정보 처리
```python
import hashlib
from cryptography.fernet import Fernet

class UserProfileService:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())
    
    def hash_sensitive_data(self, data: str) -> str:
        """민감한 데이터는 해시화하여 저장"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def encrypt_pii(self, data: str) -> str:
        """개인식별정보는 암호화하여 저장"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def process_user_profile(self, profile: UserProfile) -> UserProfile:
        # 사업자등록번호 해시화
        if profile.business_info.registration_number:
            profile.business_info.registration_number = self.hash_sensitive_data(
                profile.business_info.registration_number
            )
        
        # 상세 주소 암호화
        if profile.location.detailed_address:
            profile.location.detailed_address = self.encrypt_pii(
                profile.location.detailed_address
            )
        
        return profile
```

## 8. 로깅 및 모니터링 가이드라인

### 8.1. 구조화된 로깅
```python
import structlog
from typing import Any, Dict

# 로거 설정
logger = structlog.get_logger()

class RecommendationService:
    async def get_recommendations(self, query: str, user_profile: UserProfile):
        # 요청 시작 로깅
        logger.info(
            "recommendation_request_started",
            user_id=user_profile.user_id,
            query_length=len(query),
            business_type=user_profile.business_info.business_type
        )
        
        try:
            # 처리 과정 로깅
            candidates = await self.vector_search.find_similar(query)
            logger.info(
                "vector_search_completed",
                candidates_found=len(candidates),
                search_time_ms=search_time
            )
            
            # 성공 로깅
            logger.info(
                "recommendation_request_completed",
                recommendations_count=len(result.recommendations),
                total_time_ms=total_time
            )
            
            return result
            
        except Exception as e:
            # 에러 로깅
            logger.error(
                "recommendation_request_failed",
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
```

### 8.2. 메트릭 수집
```python
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
recommendation_requests = Counter(
    'aegis_recommendation_requests_total',
    'Total recommendation requests',
    ['status', 'business_type']
)

recommendation_duration = Histogram(
    'aegis_recommendation_duration_seconds',
    'Recommendation processing time'
)

active_users = Gauge(
    'aegis_active_users',
    'Number of active users'
)

class MetricsMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # 메트릭 기록
        duration = time.time() - start_time
        recommendation_duration.observe(duration)
        
        if request.url.path.startswith('/api/v1/recommendations'):
            recommendation_requests.labels(
                status=response.status_code,
                business_type=getattr(request.state, 'business_type', 'unknown')
            ).inc()
        
        return response
```

---

**📋 관련 문서**
- [마스터플랜](./MASTERPLAN.md)
- [구현 계획](./IMPLEMENTATION_PLAN.md)
- [시스템 아키텍처](./01_SYSTEM_ARCHITECTURE.md)
- [API 명세서](./03_DATA_MODELS_AND_APIS/API_CONTRACT.md)