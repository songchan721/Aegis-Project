# Recommendation Service Design Document

## 1. Overview

Recommendation Service는 이지스(Aegis) 시스템의 **지능형 정책 추천 엔진**으로, RAG-KG 하이브리드 아키텍처와 S.C.O.R.E. 프레임워크를 통해 개인화된 정책 추천을 제공합니다.

### 1.1 핵심 책임

1. **자연어 쿼리 처리** - 사용자의 자연스러운 질문을 이해하고 구조화
2. **RAG-KG 하이브리드 검색** - 벡터 검색과 지식 그래프 추론 결합
3. **KMRR 알고리즘** - Knowledge-Modulated Retrieval & Re-ranking
4. **S.C.O.R.E. 프레임워크** - 설명 가능한 AI 추천 (Specificity, Consistency, Observability, Reproducibility, Explainability)
5. **개인화 추천** - 사용자 프로필 및 피드백 기반 학습
6. **Living Gateway** - 다중 LLM 지원 및 폴백 체인
7. **대화형 세션 관리** - 맥락 기반 연속 대화 지원

### 1.2 역할 명확화 (중요)

**Recommendation Service의 역할:**
- ✅ 자연어 질문 이해 및 의도 분석
- ✅ RAG-KG 하이브리드 검색 수행
- ✅ 설명 가능한 추천 결과 생성
- ✅ 사용자 피드백 학습 및 개인화
- ✅ 대화형 추천 세션 관리
- ✅ 다중 LLM 관리 및 폴백
- ✅ 추천 성능 모니터링 및 최적화

**Recommendation Service가 하지 않는 것:**
- ❌ 정책 데이터 관리 (Policy Service 담당)
- ❌ 사용자 인증 및 권한 관리 (User Service 담당)
- ❌ 키워드 검색 (Search Service 담당)
- ❌ 정책 데이터 수집 및 크롤링 (Data Pipeline 담당)
- ❌ 정책 콘텐츠 생성 (Policy Service 담당)

### 1.3 설계 원칙

1. **설명 가능성 (Explainability)**: 모든 추천에 명확한 근거 제공
2. **개인화 (Personalization)**: 사용자 프로필 및 피드백 기반 맞춤 추천
3. **확장성 (Scalability)**: 대용량 사용자 및 정책 데이터 처리
4. **신뢰성 (Reliability)**: 다중 LLM 폴백으로 안정적 서비스
5. **성능 (Performance)**: 3초 이내 추천 결과 반환
6. **학습 (Learning)**: 지속적인 피드백 학습 및 개선
7. **공정성 (Fairness)**: 편향 없는 공정한 추천

### 1.4 다른 서비스와의 역할 구분

| 서비스 | 역할 | 통신 방식 | 데이터 흐름 |
|--------|------|-----------|-------------|
| **User Service** | 사용자 프로필 제공 | API 호출 | User Profile → Recommendation |
| **Policy Service** | 정책 데이터 제공 | API 호출 + 이벤트 구독 | Policy Data → Recommendation |
| **Search Service** | 키워드 검색 지원 | API 호출 | Search Results → Recommendation |
| **Data Pipeline** | 임베딩 생성 | 이벤트 구독 | Embeddings → Milvus |
| **Recommendation Service** | AI 기반 추천 | API 제공 | Recommendations → Frontend |

### 1.5 핵심 기술 스택

**AI/ML:**
- LLM: OpenAI GPT-4, Anthropic Claude, Google Gemini, Local LLM
- Embedding: sentence-transformers (paraphrase-multilingual-mpnet-base-v2)
- Framework: LangChain

**데이터베이스:**
- Vector DB: Milvus (정책 임베딩, 768차원)
- Graph DB: Neo4j (지식 그래프, 정책 관계)
- Cache: Redis (세션, 추천 결과)
- RDBMS: PostgreSQL (피드백, 세션 이력)

**백엔드:**
- Framework: FastAPI
- Language: Python 3.11+
- Async: asyncio, aiohttp

---

## 2. Shared Library Integration ⭐

이 서비스는 `aegis-shared` 공통 라이브러리를 적극 활용합니다.

### 2.1 사용하는 모듈

```python
from aegis_shared.database import BaseRepository, DatabaseManager
from aegis_shared.auth import JWTHandler, AuthMiddleware, RBAC
from aegis_shared.logging import get_logger, add_context, LogLevel
from aegis_shared.monitoring import track_metrics, MetricsCollector
from aegis_shared.errors import ErrorCode, ServiceException
from aegis_shared.cache import cache_result, RedisClient, MultiLevelCache
from aegis_shared.config import get_config
from aegis_shared.messaging import EventSubscriber, EventPublisher
```

### 2.2 왜 Shared Library를 사용하는가?

#### 2.2.1 BaseRepository로 피드백 관리

**Before (shared-library 없이):**
```python
# ❌ 문제점: 반복적인 CRUD 코드, 트랜잭션 관리 복잡
class FeedbackRepository:
    def __init__(self, session):
        self.session = session
    
    async def create_feedback(self, feedback_data: dict):
        feedback = UserFeedback(**feedback_data)
        self.session.add(feedback)
        try:
            await self.session.commit()
            await self.session.refresh(feedback)
            return feedback
        except Exception as e:
            await self.session.rollback()
            raise
    
    async def find_by_user(self, user_id: str):
        result = await self.session.execute(
            select(UserFeedback).where(UserFeedback.user_id == user_id)
        )
        return result.scalars().all()
    
    async def update_feedback(self, feedback_id: str, updates: dict):
        result = await self.session.execute(
            select(UserFeedback).where(UserFeedback.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()
        if not feedback:
            raise ValueError("Feedback not found")
        
        for key, value in updates.items():
            setattr(feedback, key, value)
        
        try:
            await self.session.commit()
            return feedback
        except Exception as e:
            await self.session.rollback()
            raise
```

**After (shared-library 사용):**
```python
# ✅ 장점: BaseRepository 상속으로 CRUD 자동화, 코드 70% 감소
from aegis_shared.database import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

class FeedbackRepository(BaseRepository[UserFeedback]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserFeedback)
    
    # create, get_by_id, update, delete, list, count 자동 제공
    
    # 도메인 특화 메서드만 추가
    async def find_by_recommendation(
        self,
        recommendation_id: str
    ) -> List[UserFeedback]:
        return await self.list(
            filters={"recommendation_id": recommendation_id},
            order_by=[("created_at", "desc")]
        )
    
    async def get_user_feedback_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        feedbacks = await self.list(
            filters={"user_id": user_id}
        )
        
        return {
            "total_count": len(feedbacks),
            "positive_count": sum(1 for f in feedbacks if f.rating >= 4),
            "negative_count": sum(1 for f in feedbacks if f.rating < 3),
            "avg_rating": sum(f.rating for f in feedbacks) / len(feedbacks) if feedbacks else 0
        }
```

**효과:**
- 코드 라인 수 70% 감소 (50줄 → 15줄)
- 트랜잭션 관리 자동화
- 에러 처리 표준화
- 일관된 API 인터페이스

#### 2.2.2 캐싱 데코레이터로 성능 향상

**Before:**
```python
# ❌ 문제점: 수동 캐싱 관리, 코드 중복, 캐시 무효화 복잡
import json
import hashlib

async def get_recommendations(user_id: str, query: str):
    # 캐시 키 생성
    cache_key = f"rec:{user_id}:{hashlib.md5(query.encode()).hexdigest()}"
    
    # 캐시 확인
    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache hit for {cache_key}")
        return json.loads(cached)
    
    # 추천 생성
    results = await generate_recommendations(user_id, query)
    
    # 캐시 저장
    await redis_client.setex(
        cache_key,
        300,  # TTL 5분
        json.dumps(results, default=str)
    )
    
    logger.info(f"Cache miss for {cache_key}")
    return results

async def invalidate_user_cache(user_id: str):
    # 사용자 관련 모든 캐시 삭제
    pattern = f"rec:{user_id}:*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
```

**After:**
```python
# ✅ 장점: 캐싱 데코레이터로 자동화, 코드 간결화
from aegis_shared.cache import cache_result, MultiLevelCache

@cache_result(
    ttl=300,
    key_prefix="recommendations",
    cache_null=False,
    serialize="json"
)
async def get_recommendations(user_id: str, query: str):
    return await generate_recommendations(user_id, query)

# 캐시 무효화도 간단
from aegis_shared.cache import invalidate_cache

async def on_user_profile_updated(user_id: str):
    await invalidate_cache(
        key_prefix="recommendations",
        pattern=f"*{user_id}*"
    )
```

**효과:**
- 코드 라인 수 80% 감소 (30줄 → 6줄)
- 캐시 관리 자동화
- 일관된 캐싱 전략
- 성능 향상 (캐시 히트 시 응답 시간 < 100ms)

#### 2.2.3 구조화된 로깅

**Before:**
```python
# ❌ 문제점: 비구조화된 로깅, 검색 어려움, 컨텍스트 누락
import logging
logger = logging.getLogger(__name__)

async def recommend(user_id: str, query: str):
    logger.info(f"Recommendation request from user {user_id}: {query}")
    
    try:
        results = await generate_recommendations(user_id, query)
        logger.info(f"Generated {len(results)} recommendations for user {user_id}")
        return results
    except Exception as e:
        logger.error(f"Recommendation failed for user {user_id}: {str(e)}")
        raise
```

**After:**
```python
# ✅ 장점: 구조화된 로깅, Elasticsearch 검색 용이, 자동 컨텍스트
from aegis_shared.logging import get_logger, add_context

logger = get_logger(__name__)

async def recommend(user_id: str, query: str):
    # 컨텍스트 자동 추가 (request_id, user_id, timestamp 등)
    add_context(user_id=user_id, query=query)
    
    logger.info(
        "recommendation_request",
        query_length=len(query),
        user_profile_complete=await check_profile_completeness(user_id)
    )
    
    try:
        start_time = time.time()
        results = await generate_recommendations(user_id, query)
        
        logger.info(
            "recommendation_success",
            results_count=len(results),
            response_time_ms=int((time.time() - start_time) * 1000),
            top_score=results[0].score if results else 0
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "recommendation_failed",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True
        )
        raise
```

**효과:**
- Elasticsearch에서 쉽게 검색 가능
- 자동 컨텍스트 추가 (request_id, user_id)
- 일관된 로그 형식
- 성능 메트릭 자동 수집

#### 2.2.4 메트릭 수집 자동화

**Before:**
```python
# ❌ 문제점: 수동 메트릭 수집, Prometheus 연동 복잡
from prometheus_client import Counter, Histogram
import time

recommendation_requests = Counter(
    'recommendation_requests_total',
    'Total recommendation requests'
)
recommendation_latency = Histogram(
    'recommendation_latency_seconds',
    'Recommendation latency'
)

async def recommend(user_id: str, query: str):
    recommendation_requests.inc()
    start_time = time.time()
    
    try:
        results = await generate_recommendations(user_id, query)
        return results
    finally:
        recommendation_latency.observe(time.time() - start_time)
```

**After:**
```python
# ✅ 장점: 메트릭 수집 자동화, 데코레이터로 간단
from aegis_shared.monitoring import track_metrics

@track_metrics(
    metric_name="recommendation",
    track_latency=True,
    track_errors=True,
    labels=["user_id", "query_type"]
)
async def recommend(user_id: str, query: str, query_type: str = "general"):
    results = await generate_recommendations(user_id, query)
    return results
```

**효과:**
- 코드 라인 수 90% 감소 (15줄 → 1줄)
- 자동 메트릭 수집 (요청 수, 지연 시간, 에러율)
- Prometheus 연동 자동화
- Grafana 대시보드 자동 생성

#### 2.2.5 중앙 에러 코드 관리

**Before:**
```python
# ❌ 문제점: 에러 코드 중복, 일관성 부족, 관리 어려움
class RecommendationError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)

# 각 서비스마다 다른 에러 코드
raise RecommendationError("User not found", "REC_001")
raise RecommendationError("LLM failed", "REC_002")
raise RecommendationError("Invalid query", "REC_003")
```

**After:**
```python
# ✅ 장점: 중앙 에러 코드 레지스트리, 일관된 에러 처리
from aegis_shared.errors import ErrorCode, ServiceException

# 중앙 에러 코드 레지스트리에서 관리
raise ServiceException(
    error_code=ErrorCode.USER_NOT_FOUND,
    message="User profile not found",
    details={"user_id": user_id}
)

raise ServiceException(
    error_code=ErrorCode.LLM_SERVICE_UNAVAILABLE,
    message="All LLM providers failed",
    details={"providers_tried": ["openai", "claude", "gemini"]}
)

raise ServiceException(
    error_code=ErrorCode.INVALID_INPUT,
    message="Query is too short",
    details={"query_length": len(query), "min_length": 3}
)
```

**효과:**
- 에러 코드 중복 방지
- 일관된 에러 응답 형식
- 에러 추적 및 분석 용이
- 프론트엔드 에러 처리 간소화
---

## 3. Architecture

### 3.1 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Application]
        MOBILE[Mobile App]
        API_CLIENT[API Clients]
    end
    
    subgraph "API Gateway"
        GATEWAY[API Gateway<br/>인증, 라우팅]
    end
    
    subgraph "Recommendation Service"
        subgraph "API Layer"
            REC_API[Recommendation API]
            FEEDBACK_API[Feedback API]
            SESSION_API[Session API]
            HEALTH[Health Check]
        end
        
        subgraph "Query Processing"
            QUERY_PARSER[Query Parser]
            INTENT_ANALYZER[Intent Analyzer]
            ENTITY_EXTRACTOR[Entity Extractor]
            CONTEXT_BUILDER[Context Builder]
        end
        
        subgraph "AI Core Engine"
            LIVING_GW[Living Gateway<br/>다중 LLM 관리]
            RAG_ENGINE[RAG Engine<br/>벡터 검색]
            KG_REASONER[KG Reasoner<br/>지식 그래프 추론]
            KMRR_RANKER[KMRR Ranker<br/>최종 순위 결정]
        end
        
        subgraph "Explanation Engine"
            SCORE_CALC[S.C.O.R.E Calculator]
            EVIDENCE_GEN[Evidence Generator]
            EXPLANATION_BUILD[Explanation Builder]
        end
        
        subgraph "Learning & Optimization"
            FEEDBACK_PROC[Feedback Processor]
            PERSONALIZATION[Personalization Engine]
            AB_TESTER[A/B Tester]
            PERF_OPT[Performance Optimizer]
        end
    end
    
    subgraph "External Services"
        OPENAI[OpenAI GPT-4]
        CLAUDE[Anthropic Claude]
        GEMINI[Google Gemini]
        LOCAL_LLM[Local LLM]
        POLICY_SVC[Policy Service]
        USER_SVC[User Service]
        SEARCH_SVC[Search Service]
    end
    
    subgraph "Data Storage"
        MILVUS[(Milvus<br/>Vector DB)]
        NEO4J[(Neo4j<br/>Graph DB)]
        REDIS[(Redis<br/>Cache)]
        POSTGRES[(PostgreSQL<br/>Feedback/Session)]
    end
    
    subgraph "Message Queue"
        KAFKA[Apache Kafka]
    end
    
    WEB --> GATEWAY
    MOBILE --> GATEWAY
    API_CLIENT --> GATEWAY
    GATEWAY --> REC_API
    GATEWAY --> FEEDBACK_API
    GATEWAY --> SESSION_API
    
    REC_API --> QUERY_PARSER
    QUERY_PARSER --> INTENT_ANALYZER
    INTENT_ANALYZER --> ENTITY_EXTRACTOR
    ENTITY_EXTRACTOR --> CONTEXT_BUILDER
    
    CONTEXT_BUILDER --> LIVING_GW
    LIVING_GW --> RAG_ENGINE
    RAG_ENGINE --> KG_REASONER
    KG_REASONER --> KMRR_RANKER
    
    KMRR_RANKER --> SCORE_CALC
    SCORE_CALC --> EVIDENCE_GEN
    EVIDENCE_GEN --> EXPLANATION_BUILD
    
    LIVING_GW --> OPENAI
    LIVING_GW --> CLAUDE
    LIVING_GW --> GEMINI
    LIVING_GW --> LOCAL_LLM
    
    RAG_ENGINE --> MILVUS
    KG_REASONER --> NEO4J
    SESSION_API --> REDIS
    FEEDBACK_API --> POSTGRES
    
    RAG_ENGINE --> POLICY_SVC
    PERSONALIZATION --> USER_SVC
    KG_REASONER --> SEARCH_SVC
    
    POLICY_SVC --> KAFKA
    KAFKA --> FEEDBACK_PROC
```


### 3.2 KMRR 알고리즘 플로우

```mermaid
sequenceDiagram
    participant User
    participant Parser as Query Parser
    participant LivingGW as Living Gateway
    participant RAG as RAG Engine
    participant KG as Knowledge Graph
    participant KMRR as KMRR Ranker
    participant SCORE as S.C.O.R.E.
    
    User->>Parser: "경기도 카페 창업 운영자금 필요"
    Parser->>Parser: 의도 분석 & 엔티티 추출
    Parser->>LivingGW: 구조화된 쿼리
    
    Note over LivingGW,KG: RAG-KG 하이브리드 검색
    
    LivingGW->>RAG: 쿼리 임베딩 생성
    RAG->>RAG: Milvus 벡터 검색
    RAG-->>KG: 후보 정책 (Top 50)
    
    KG->>KG: 지식 그래프 추론
    KG->>KG: 자격 요건 검증
    KG->>KG: 정책 간 관계 분석
    KG-->>KMRR: 지식 사실 (Knowledge Facts)
    
    KMRR->>KMRR: 벡터 유사도 + 지식 사실 통합
    KMRR->>KMRR: 비즈니스 규칙 적용
    KMRR->>KMRR: 최종 점수 계산
    KMRR-->>SCORE: 순위 결정된 결과 (Top 10)
    
    SCORE->>SCORE: S.C.O.R.E. 점수 계산
    SCORE->>SCORE: 증거 체인 생성
    SCORE->>SCORE: 설명 텍스트 생성
    SCORE-->>User: 추천 결과 + 설명
```

### 3.3 Living Gateway 폴백 체인

```mermaid
graph LR
    Request[추천 요청] --> Primary[Primary: OpenAI GPT-4]
    Primary -->|성공| Success[응답 반환]
    Primary -->|실패/타임아웃| Secondary[Secondary: Claude]
    Secondary -->|성공| Success
    Secondary -->|실패| Tertiary[Tertiary: Gemini]
    Tertiary -->|성공| Success
    Tertiary -->|실패| LocalLLM[Local LLM]
    LocalLLM -->|성공| Success
    LocalLLM -->|실패| RuleBased[규칙 기반 폴백]
    RuleBased --> Success
```


### 3.4 데이터 흐름

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Cache
    participant RAG
    participant KG
    participant DB
    
    User->>API: 추천 요청
    API->>Cache: 캐시 확인
    
    alt 캐시 히트
        Cache-->>API: 캐시된 결과
        API-->>User: 즉시 반환 (< 1초)
    else 캐시 미스
        API->>RAG: 벡터 검색
        RAG->>KG: 지식 그래프 추론
        KG->>DB: 사용자 프로필 조회
        DB-->>KG: 프로필 데이터
        KG-->>API: 추천 결과
        API->>Cache: 결과 캐싱
        API-->>User: 추천 반환 (< 3초)
    end
    
    User->>API: 피드백 제공
    API->>DB: 피드백 저장
    API->>Cache: 관련 캐시 무효화
```

### 3.5 이벤트 기반 통신

```mermaid
graph LR
    subgraph "Event Publishers"
        POLICY[Policy Service]
        USER[User Service]
    end
    
    subgraph "Kafka Topics"
        POLICY_TOPIC[policy-events]
        USER_TOPIC[user-events]
    end
    
    subgraph "Event Subscribers"
        REC[Recommendation Service]
    end
    
    POLICY -->|policy.created<br/>policy.updated<br/>policy.deleted| POLICY_TOPIC
    USER -->|user.profile_updated| USER_TOPIC
    
    POLICY_TOPIC -->|구독| REC
    USER_TOPIC -->|구독| REC
    
    REC -->|캐시 무효화<br/>모델 재학습| REC
```

---


## 4. Components and Interfaces

### 4.1 Query Processing Layer

#### 4.1.1 Query Parser

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from aegis_shared.logging import get_logger
from aegis_shared.monitoring import track_metrics

logger = get_logger(__name__)

@dataclass
class ParsedQuery:
    """파싱된 쿼리"""
    original_text: str
    intent: str  # find_policy, compare_policies, check_eligibility
    entities: Dict[str, any]  # {region, industry, amount, etc}
    confidence: float
    ambiguities: List[str]
    context_requirements: List[str]

class QueryParser:
    """자연어 쿼리 파서"""
    
    def __init__(self, living_gateway: 'LivingGateway'):
        self.living_gateway = living_gateway
        self.intent_analyzer = IntentAnalyzer()
        self.entity_extractor = EntityExtractor()
    
    @track_metrics("query_parser_parse")
    async def parse_query(
        self,
        query: str,
        user_profile: 'UserProfile',
        session_context: Optional['SessionContext'] = None
    ) -> ParsedQuery:
        """자연어 쿼리를 구조화된 형태로 파싱"""
        
        logger.info(
            "parsing_query",
            query=query,
            user_id=user_profile.user_id,
            has_context=session_context is not None
        )
        
        # 1. 의도 분석
        intent = await self.intent_analyzer.analyze(
            query,
            session_context
        )
        
        # 2. 엔티티 추출
        entities = await self.entity_extractor.extract(
            query,
            user_profile
        )
        
        # 3. 모호성 감지
        ambiguities = self._detect_ambiguities(query, entities)
        
        # 4. 컨텍스트 요구사항 식별
        context_reqs = self._identify_context_requirements(
            intent,
            entities,
            user_profile
        )
        
        parsed = ParsedQuery(
            original_text=query,
            intent=intent.type,
            entities=entities,
            confidence=intent.confidence,
            ambiguities=ambiguities,
            context_requirements=context_reqs
        )
        
        logger.info(
            "query_parsed",
            intent=parsed.intent,
            entities_count=len(parsed.entities),
            confidence=parsed.confidence,
            has_ambiguities=len(parsed.ambiguities) > 0
        )
        
        return parsed
```

#### 4.1.2 Living Gateway

```python
from typing import Optional, List
from enum import Enum
import asyncio
from aegis_shared.errors import ServiceException, ErrorCode

class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    LOCAL = "local"

class LivingGateway:
    """다중 LLM 관리 게이트웨이"""
    
    def __init__(self):
        self.providers = {
            LLMProvider.OPENAI: OpenAIClient(),
            LLMProvider.CLAUDE: ClaudeClient(),
            LLMProvider.GEMINI: GeminiClient(),
            LLMProvider.LOCAL: LocalLLMClient()
        }
        self.health_monitor = ProviderHealthMonitor()
        self.fallback_chain = [
            LLMProvider.OPENAI,
            LLMProvider.CLAUDE,
            LLMProvider.GEMINI,
            LLMProvider.LOCAL
        ]


## 5. Data Models

### 5.1 API 모델 (Pydantic)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class RecommendationRequest(BaseModel):
    """추천 요청 모델"""
    session_id: Optional[str] = None
    query: str = Field(..., min_length=1, max_length=1000, description="사용자 질문")
    user_id: str = Field(..., description="사용자 ID")
    preferences: Optional['RecommendationPreferences'] = None
    context: Optional[Dict[str, any]] = Field(default_factory=dict)
    
    @validator('query')
    def validate_query(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Query must be at least 3 characters")
        return v.strip()

class RecommendationPreferences(BaseModel):
    """추천 설정"""
    max_results: int = Field(default=10, ge=1, le=50)
    include_explanations: bool = True
    explanation_detail_level: str = Field(default="standard", regex="^(basic|standard|detailed)$")
    sort_by: str = Field(default="relevance", regex="^(relevance|amount|deadline|popularity)$")
    diversity_factor: float = Field(default=0.3, ge=0, le=1)

class PolicyRecommendation(BaseModel):
    """정책 추천 결과"""
    rank: int
    policy_id: str
    title: str
    description: str
    category: str
    organization: str
    relevance_score: float = Field(..., ge=0, le=1)
    score_breakdown: 'ScoreBreakdown'
    explanation: Optional['RecommendationExplanation'] = None
    confidence_level: str = Field(..., regex="^(high|medium|low)$")
    metadata: Dict[str, any] = Field(default_factory=dict)

class ScoreBreakdown(BaseModel):
    """점수 세부 분석"""
    final_score: float = Field(..., ge=0, le=1)
    vector_similarity: float = Field(..., ge=0, le=1)
    kg_boost_factor: float = Field(..., ge=0, le=1)
    business_rule_adjustment: float = Field(..., ge=-0.5, le=0.5)
    personalization_bonus: float = Field(..., ge=0, le=0.3)
    diversity_penalty: float = Field(..., ge=-0.2, le=0)


## 6. Production Considerations ⭐

### 6.1 확장성 (Scalability)

#### 6.1.1 Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: recommendation-service-hpa
  namespace: aegis
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: recommendation-service
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
        name: recommendation_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 30
      selectPolicy: Max
```

**설명:**
- 최소 3개, 최대 20개 Pod 유지
- CPU 70%, 메모리 80% 기준 스케일링
- 초당 100 요청 기준 추가 스케일링
- 스케일 다운 안정화 5분, 스케일 업 1분


#### 6.1.2 리소스 요청 및 제한

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recommendation-service
spec:
  template:
    spec:
      containers:
      - name: recommendation-service
        image: aegis/recommendation-service:latest
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        env:
        - name: WORKERS
          value: "4"
        - name: MAX_CONCURRENT_REQUESTS
          value: "100"
```

**근거:**
- CPU: 1코어 요청, 2코어 제한 (LLM 호출 및 벡터 검색 처리)
- Memory: 2GB 요청, 4GB 제한 (임베딩 모델 및 캐시)
- Workers: 4개 (비동기 처리 최적화)

### 6.2 장애 복구 (Disaster Recovery)

#### 6.2.1 Circuit Breaker 패턴

```python
from circuitbreaker import circuit
from aegis_shared.errors import ServiceException, ErrorCode

class ExternalServiceClient:
    """외부 서비스 클라이언트 (Circuit Breaker 적용)"""
    
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=ServiceException)
    async def call_policy_service(self, policy_id: str):
        """Policy Service 호출 (Circuit Breaker 적용)"""
        try:
            response = await self.http_client.get(
                f"{self.policy_service_url}/policies/{policy_id}",
                timeout=5.0
            )
            return response.json()
        except asyncio.TimeoutError:
            raise ServiceException(
                error_code=ErrorCode.SERVICE_TIMEOUT,
                message="Policy Service timeout"
            )
        except Exception as e:
            raise ServiceException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Policy Service error: {str(e)}"
            )
```

**설정:**
- failure_threshold: 5회 연속 실패 시 Circuit Open
- recovery_timeout: 60초 후 Half-Open 상태로 전환
- Circuit Open 시 즉시 실패 반환 (빠른 실패)


## 7. Service Integration

### 7.1 이벤트 발행/구독 (Kafka)

#### 7.1.1 구독하는 이벤트

| Topic | Event Type | Consumer Group | 처리 로직 | DLQ 전략 |
|-------|-----------|----------------|----------|----------|
| policy-events | policy.created | recommendation-service-policy | 정책 임베딩 생성 및 캐시 무효화 | 3회 재시도 후 DLQ |
| policy-events | policy.updated | recommendation-service-policy | 정책 임베딩 업데이트 및 캐시 무효화 | 3회 재시도 후 DLQ |
| policy-events | policy.deleted | recommendation-service-policy | 정책 임베딩 삭제 및 캐시 무효화 | 3회 재시도 후 DLQ |
| user-events | user.profile_updated | recommendation-service-user | 사용자 캐시 무효화 및 개인화 모델 업데이트 | 3회 재시도 후 DLQ |

#### 7.1.2 이벤트 구독 구현

```python
from aegis_shared.messaging import EventSubscriber, VersionedEvent
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class PolicyEventHandler:
    """정책 이벤트 핸들러"""
    
    def __init__(
        self,
        cache_manager: 'CacheManager',
        embedding_service: 'EmbeddingService'
    ):
        self.cache_manager = cache_manager
        self.embedding_service = embedding_service
        self.subscriber = EventSubscriber(
            topics=['policy-events'],
            group_id='recommendation-service-policy'
        )
    
    async def start(self):
        """이벤트 구독 시작"""
        async for event in self.subscriber.consume():
            await self.handle_event(event)
    
    async def handle_event(self, event: VersionedEvent):
        """이벤트 처리"""
        try:
            if event.event_type == 'policy.created':
                await self._handle_policy_created(event.data)
            elif event.event_type == 'policy.updated':
                await self._handle_policy_updated(event.data)
            elif event.event_type == 'policy.deleted':
                await self._handle_policy_deleted(event.data)
            
            logger.info(
                "policy_event_processed",
                event_type=event.event_type,
                policy_id=event.data.get('policy_id')
            )
            
        except Exception as e:
            logger.error(
                "policy_event_processing_failed",
                event_type=event.event_type,
                error=str(e),
                exc_info=True
            )
            raise


## 8. Error Handling ⭐

### 8.1 중앙 에러 코드 레지스트리

```python
from aegis_shared.errors import ErrorCode, ServiceException
from enum import Enum

class RecommendationErrorCode(str, Enum):
    """추천 서비스 에러 코드"""
    
    # Query Processing Errors (REC_1xxx)
    QUERY_TOO_SHORT = "REC_1001"
    QUERY_TOO_LONG = "REC_1002"
    INVALID_QUERY_FORMAT = "REC_1003"
    AMBIGUOUS_QUERY = "REC_1004"
    MISSING_CONTEXT = "REC_1005"
    
    # LLM Errors (REC_2xxx)
    LLM_SERVICE_UNAVAILABLE = "REC_2001"
    LLM_TIMEOUT = "REC_2002"
    LLM_RATE_LIMIT = "REC_2003"
    LLM_INVALID_RESPONSE = "REC_2004"
    ALL_LLM_FAILED = "REC_2005"
    
    # Vector Search Errors (REC_3xxx)
    MILVUS_CONNECTION_ERROR = "REC_3001"
    MILVUS_SEARCH_FAILED = "REC_3002"
    EMBEDDING_GENERATION_FAILED = "REC_3003"
    NO_CANDIDATES_FOUND = "REC_3004"
    
    # Knowledge Graph Errors (REC_4xxx)
    NEO4J_CONNECTION_ERROR = "REC_4001"
    NEO4J_QUERY_FAILED = "REC_4002"
    REASONING_FAILED = "REC_4003"
    
    # Recommendation Errors (REC_5xxx)
    INSUFFICIENT_USER_PROFILE = "REC_5001"
    NO_RECOMMENDATIONS_GENERATED = "REC_5002"
    SCORING_FAILED = "REC_5003"
    EXPLANATION_GENERATION_FAILED = "REC_5004"
    
    # Session Errors (REC_6xxx)
    SESSION_NOT_FOUND = "REC_6001"
    SESSION_EXPIRED = "REC_6002"
    SESSION_CREATION_FAILED = "REC_6003"
    
    # Cache Errors (REC_7xxx)
    CACHE_CONNECTION_ERROR = "REC_7001"
    CACHE_OPERATION_FAILED = "REC_7002"
```

### 8.2 에러 처리 전략

```python
from typing import Optional
from aegis_shared.logging import get_logger

logger = get_logger(__name__)

class RecommendationServiceErrorHandler:
    """추천 서비스 에러 핸들러"""
    
    async def handle_llm_failure(
        self,
        query: str,
        error: Exception
    ) -> Optional['ParsedQuery']:
        """LLM 실패 시 폴백 처리"""
        
        logger.warning(
            "llm_failure_fallback",
            error_type=type(error).__name__,
            error_message=str(error)
        )
        
        # 규칙 기반 파서로 폴백
        try:
            return await self.rule_based_parser.parse(query)
        except Exception as e:
            logger.error(
                "fallback_parser_failed",
                error=str(e),
                exc_info=True
            )
            raise ServiceException(
                error_code=RecommendationErrorCode.ALL_LLM_FAILED,
                message="All LLM providers and fallback failed",
                details={"original_error": str(error)}
            )


## 9. Monitoring

### 9.1 Prometheus 메트릭

```python
from prometheus_client import Counter, Histogram, Gauge, Summary
from aegis_shared.monitoring import track_metrics

# 요청 메트릭
recommendation_requests_total = Counter(
    'recommendation_requests_total',
    'Total recommendation requests',
    ['endpoint', 'status']
)

recommendation_latency = Histogram(
    'recommendation_latency_seconds',
    'Recommendation latency',
    ['endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

# LLM 메트릭
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'status']
)

llm_latency = Histogram(
    'llm_latency_seconds',
    'LLM request latency',
    ['provider'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

llm_fallback_count = Counter(
    'llm_fallback_count',
    'LLM fallback count',
    ['from_provider', 'to_provider']
)

# 벡터 검색 메트릭
vector_search_latency = Histogram(
    'vector_search_latency_seconds',
    'Vector search latency',
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0]
)

vector_search_candidates = Histogram(
    'vector_search_candidates',
    'Number of candidates from vector search',
    buckets=[10, 20, 50, 100, 200]
)

# 지식 그래프 메트릭
kg_reasoning_latency = Histogram(
    'kg_reasoning_latency_seconds',
    'Knowledge graph reasoning latency',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# 추천 품질 메트릭
recommendation_score = Summary(
    'recommendation_score',
    'Recommendation score distribution'
)

recommendation_diversity = Gauge(
    'recommendation_diversity',
    'Recommendation diversity score'
)

# 캐시 메트릭
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate',
    ['cache_type']
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status']
)
```


### 9.2 Grafana 대시보드

#### 9.2.1 서비스 대시보드 (JSON)

```json
{
  "dashboard": {
    "title": "Recommendation Service Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(recommendation_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Response Time (p50, p95, p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(recommendation_latency_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(recommendation_latency_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(recommendation_latency_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(recommendation_requests_total{status=\"error\"}[5m]) / rate(recommendation_requests_total[5m])"
          }
        ]
      },
      {
        "title": "LLM Provider Status",
        "targets": [
          {
            "expr": "rate(llm_requests_total{status=\"success\"}[5m]) by (provider)"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "cache_hit_rate"
          }
        ]
      }
    ]
  }
}
```

### 9.3 알림 규칙 (Prometheus Alertmanager)

```yaml
groups:
- name: recommendation_service_alerts
  interval: 30s
  rules:
  # 높은 에러율
  - alert: HighErrorRate
    expr: |
      rate(recommendation_requests_total{status="error"}[5m]) 
      / rate(recommendation_requests_total[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
      service: recommendation-service
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
  
  # 느린 응답 시간
  - alert: SlowResponseTime
    expr: |
      histogram_quantile(0.95, 
        rate(recommendation_latency_seconds_bucket[5m])
      ) > 3.0
    for: 5m
    labels:
      severity: warning
      service: recommendation-service
    annotations:
      summary: "Slow response time detected"
      description: "P95 latency is {{ $value }}s (threshold: 3s)"
  
  # LLM 서비스 장애
  - alert: LLMServiceDown
    expr: |
      rate(llm_requests_total{status="success"}[5m]) == 0
    for: 2m
    labels:
      severity: critical
      service: recommendation-service
    annotations:
      summary: "LLM service is down"
      description: "No successful LLM requests in the last 2 minutes"
  
  # 캐시 히트율 저하
  - alert: LowCacheHitRate
    expr: cache_hit_rate < 0.5
    for: 10m
    labels:
      severity: warning
      service: recommendation-service
    annotations:
      summary: "Low cache hit rate"
      description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 50%)"
```

---


## 10. Database Schema

### 10.1 PostgreSQL 스키마

```sql
-- 추천 세션 테이블
CREATE TABLE recommendation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    session_start TIMESTAMP NOT NULL DEFAULT NOW(),
    session_end TIMESTAMP,
    query_count INTEGER DEFAULT 0,
    context JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_created_at (created_at)
);

-- 사용자 피드백 테이블
CREATE TABLE user_feedbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    recommendation_id UUID NOT NULL,
    policy_id VARCHAR(255) NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type VARCHAR(50) NOT NULL, -- explicit, implicit
    action VARCHAR(50), -- view, click, apply, dismiss
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_feedbacks_user_id (user_id),
    INDEX idx_feedbacks_policy_id (policy_id),
    INDEX idx_feedbacks_created_at (created_at)
);

-- 추천 이력 테이블
CREATE TABLE recommendation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES recommendation_sessions(id),
    user_id VARCHAR(255) NOT NULL,
    query TEXT NOT NULL,
    parsed_query JSONB,
    recommendations JSONB NOT NULL,
    response_time_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_history_session_id (session_id),
    INDEX idx_history_user_id (user_id),
    INDEX idx_history_created_at (created_at)
);

-- 사용자 선호도 테이블
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL UNIQUE,
    preferred_categories JSONB,
    preferred_organizations JSONB,
    preferred_amount_range JSONB,
    interaction_history JSONB,
    personalization_weights JSONB,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_preferences_user_id (user_id)
);
```

### 10.2 Milvus 컬렉션 스키마

```python
from pymilvus import CollectionSchema, FieldSchema, DataType

# 정책 임베딩 컬렉션
policy_embeddings_schema = CollectionSchema(
    fields=[
        FieldSchema(name="policy_id", dtype=DataType.VARCHAR, max_length=255, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="region", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="organization", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="created_at", dtype=DataType.INT64)
    ],
    description="Policy embeddings for vector search"
)

# 인덱스 설정
index_params = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}
```


### 10.3 Neo4j 그래프 스키마

```cypher
-- 노드 레이블
CREATE CONSTRAINT policy_id_unique IF NOT EXISTS
FOR (p:Policy) REQUIRE p.policy_id IS UNIQUE;

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

-- 인덱스
CREATE INDEX policy_category_idx IF NOT EXISTS
FOR (p:Policy) ON (p.category);

CREATE INDEX policy_region_idx IF NOT EXISTS
FOR (p:Policy) ON (p.region);

-- 정책 노드
(:Policy {
  policy_id: String,
  title: String,
  category: String,
  region: String,
  organization: String,
  support_amount: Integer,
  created_at: DateTime
})

-- 요구사항 노드
(:Requirement {
  requirement_id: String,
  type: String,  -- region, industry, business_age, revenue, employee_count
  value: String,
  operator: String,  -- eq, gte, lte, in
  description: String
})

-- 관계 타입
(:Policy)-[:HAS_REQUIREMENT]->(:Requirement)
(:Policy)-[:RELATED_TO]->(:Policy)
(:Policy)-[:SIMILAR_TO]->(:Policy)
(:Policy)-[:ALTERNATIVE_TO]->(:Policy)
(:Policy)-[:REQUIRES]->(:Policy)  -- 선행 조건
(:Policy)-[:EXCLUDES]->(:Policy)  -- 배타적 조건
```

### 10.4 Redis 캐시 스키마

```python
# 캐시 키 네이밍 컨벤션
CACHE_KEYS = {
    # 추천 결과 캐시
    "recommendations": "rec:recommendations:{user_id}:{query_hash}",
    
    # 사용자 프로필 캐시
    "user_profile": "rec:user_profile:{user_id}",
    
    # 세션 캐시
    "session": "rec:session:{session_id}",
    
    # 정책 메타데이터 캐시
    "policy_metadata": "rec:policy:{policy_id}",
    
    # LLM 응답 캐시
    "llm_response": "rec:llm:{provider}:{prompt_hash}"
}

# TTL 설정
CACHE_TTL = {
    "recommendations": 300,  # 5분
    "user_profile": 3600,  # 1시간
    "session": 1800,  # 30분
    "policy_metadata": 7200,  # 2시간
    "llm_response": 600  # 10분
}
```

### 10.5 데이터베이스 연결 풀 설정

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# PostgreSQL 연결 풀
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/recommendation_db",
    pool_size=20,  # 기본 연결 수
    max_overflow=10,  # 추가 연결 수
    pool_timeout=30,  # 대기 시간 (초)
    pool_recycle=3600,  # 재사용 시간 (초)
    pool_pre_ping=True,  # 연결 상태 확인
    echo=False
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```
---

## 11. API Specification

### 11.1 OpenAPI 스펙

```yaml
openapi: 3.0.0
info:
  title: Recommendation Service API
  version: 1.0.0
  description: AI-powered policy recommendation service

servers:
  - url: https://api.aegis.com/v1
    description: Production
  - url: https://api-staging.aegis.com/v1
    description: Staging

paths:
  /recommendations:
    post:
      summary: Generate policy recommendations
      tags: [Recommendations]
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RecommendationRequest'
      responses:
        '200':
          description: Successful recommendation
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RecommendationResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/TooManyRequests'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /recommendations/{recommendation_id}:
    get:
      summary: Get recommendation by ID
      tags: [Recommendations]
      security:
        - BearerAuth: []
      parameters:
        - name: recommendation_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Recommendation found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RecommendationResponse'
        '404':
          $ref: '#/components/responses/NotFound'

  /feedback:
    post:
      summary: Submit user feedback
      tags: [Feedback]
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FeedbackRequest'
      responses:
        '201':
          description: Feedback submitted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FeedbackResponse'
```
---
## 12. Configuration Management

### 12.1 환경 변수

```python
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    """서비스 설정"""
    
    # 서비스 기본 설정
    SERVICE_NAME: str = "recommendation-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", regex="^(development|staging|production)$")
    LOG_LEVEL: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # API 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_TIMEOUT: int = 30
    
    # 데이터베이스 설정
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10
    
    # Redis 설정
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 50
    
    # Milvus 설정
    MILVUS_HOST: str
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "policy_embeddings"
    
    # Neo4j 설정
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    
    # Kafka 설정
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_CONSUMER_GROUP: str = "recommendation-service"
    
    # LLM 설정
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # 추천 설정
    MAX_RECOMMENDATIONS: int = 10
    VECTOR_SEARCH_TOP_K: int = 50
    RECOMMENDATION_TIMEOUT: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```
## 13. Testing Strategy

### 13.1 단위 테스트

```python
import pytest
from unittest.mock import AsyncMock, Mock, patch
from recommendation_service.query_processing import QueryParser
from recommendation_service.ai_core import LivingGateway

class TestQueryParser:
    """Query Parser 단위 테스트"""
    
    @pytest.fixture
    def mock_living_gateway(self):
        return AsyncMock(spec=LivingGateway)
    
    @pytest.fixture
    def query_parser(self, mock_living_gateway):
        return QueryParser(living_gateway=mock_living_gateway)
    
    @pytest.mark.asyncio
    async def test_parse_simple_query(self, query_parser):
        # Given
        query = "경기도 카페 창업 자금 지원"
        user_profile = Mock(user_id="user123", region="경기도", industry="음식점업")
        
        # When
        result = await query_parser.parse_query(query, user_profile)
        
        # Then
        assert result.original_text == query
        assert result.intent == "find_policy"
        assert "region" in result.entities
        assert result.entities["region"] == "경기도"
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_parse_ambiguous_query(self, query_parser):
        # Given
        query = "자금 지원"  # 모호한 쿼리
        user_profile = Mock(user_id="user123", region=None, industry=None)
        
        # When
        result = await query_parser.parse_query(query, user_profile)
        
        # Then
        assert len(result.ambiguities) > 0
        assert len(result.context_requirements) > 0

class TestLivingGateway:
    """Living Gateway 단위 테스트"""
    
    @pytest.fixture
    def living_gateway(self):
        return LivingGateway()
    
    @pytest.mark.asyncio
    async def test_llm_fallback_chain(self, living_gateway):
        # Given
        prompt = "Test prompt"
        
        # Mock primary provider failure
        with patch.object(living_gateway.providers[LLMProvider.OPENAI], 'complete', side_effect=Exception("API Error")):
            # Mock secondary provider success
            with patch.object(living_gateway.providers[LLMProvider.CLAUDE], 'complete', return_value="Success"):
                # When
                result = await living_gateway.complete(prompt, "test")
                
                # Then
                assert result == "Success"
```

### 13.2 통합 테스트

```python
import pytest
from httpx import AsyncClient
from recommendation_service.main import app

@pytest.mark.integration
class TestRecommendationAPI:
    """추천 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_recommendation_end_to_end(self):
        # Given
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "경기도 카페 창업 운영자금",
                "user_id": "test_user_123"
            }
            
            # When
            response = await client.post("/api/v1/recommendations", json=request_data)
            
            # Then
            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0
            assert data["recommendations"][0]["rank"] == 1
```
## 14. Deployment

### 14.1 Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recommendation-service
  namespace: aegis
  labels:
    app: recommendation-service
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: recommendation-service
  template:
    metadata:
      labels:
        app: recommendation-service
        version: v1.0.0
    spec:
      containers:
      - name: recommendation-service
        image: aegis/recommendation-service:1.0.0
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: POSTGRES_HOST
          valueFrom:
            configMapKeyRef:
              name: recommendation-config
              key: postgres_host
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: recommendation-secrets
              key: postgres_password
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

### 14.2 Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: recommendation-service
  namespace: aegis
spec:
  type: ClusterIP
  selector:
    app: recommendation-service
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
```

---
