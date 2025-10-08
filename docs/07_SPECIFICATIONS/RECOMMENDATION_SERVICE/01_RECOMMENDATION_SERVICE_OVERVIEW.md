# 추천 서비스 명세서 (Recommendation Service Specification)

| 항목 | 내용 |
|------|------|
| 문서 ID | AAS-REC-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 서비스 개요 (Service Overview)

추천 서비스는 이지스 시스템의 핵심 두뇌로서, 사용자의 자연어 질문과 프로필 정보를 바탕으로 최적의 정책자금을 추천하는 역할을 담당한다. 본 서비스는 **상호작용 AI 코어(Interactive AI Core)**와 **살아있는 게이트웨이(Living Gateway)**를 통합하여, 단순한 검색을 넘어 논리적으로 검증된 맞춤형 솔루션을 제공한다.

### 1.1. 핵심 책임 (Core Responsibilities)
- 사용자 쿼리의 의도 파악 및 구조화
- RAG-KG 하이브리드 검색을 통한 후보 정책 발굴
- KMRR 알고리즘을 통한 지능형 재순위
- S.C.O.R.E. 프레임워크 기반 추천 근거 생성
- 사용자 피드백 수집 및 학습

### 1.2. 서비스 경계 (Service Boundaries)
**포함하는 기능:**
- 자연어 쿼리 처리 및 의도 분석
- 벡터 검색 및 지식 그래프 추론
- 추천 결과 생성 및 설명 제공
- 추천 이력 관리

**포함하지 않는 기능:**
- 사용자 인증 및 권한 관리 (User Service 담당)
- 정책 데이터 수집 및 관리 (Policy Service 담당)
- 외부 LLM 직접 호출 (Living Gateway 담당)

## 2. 아키텍처 설계 (Architecture Design)

### 2.1. 서비스 구조
```
┌─────────────────────────────────────────────────────────────┐
│                 Recommendation Service                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Query Parser  │  │  Search Engine  │  │   Explainer  │ │
│  │                 │  │                 │  │              │ │
│  │ - Intent Analysis│  │ - Vector Search │  │ - Reasoning  │ │
│  │ - Entity Extract│  │ - KG Reasoning  │  │ - Evidence   │ │
│  │ - Context Build │  │ - KMRR Ranking  │  │ - Scoring    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Feedback Engine │  │ History Manager │  │ Cache Layer  │ │
│  │                 │  │                 │  │              │ │
│  │ - Rating Process│  │ - Session Track │  │ - Result     │ │
│  │ - Learning Loop │  │ - Analytics     │  │ - Query      │ │
│  │ - Rule Update   │  │ - Audit Trail   │  │ - Profile    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. 데이터 흐름 (Data Flow)
```
[User Query] → [Query Parser] → [Search Engine] → [Explainer] → [Response]
     ↓              ↓               ↓              ↓
[User Profile] → [Context Build] → [KMRR Ranking] → [Evidence Gen]
     ↓              ↓               ↓              ↓
[History] ← [History Manager] ← [Feedback Engine] ← [User Feedback]
```

## 3. 핵심 컴포넌트 상세 (Core Components)

### 3.1. Query Parser (쿼리 파서)
사용자의 자연어 질문을 구조화된 검색 쿼리로 변환한다.

**주요 기능:**
- **의도 분석**: 질문의 목적 파악 (정보 요청, 추천 요청, 비교 요청 등)
- **개체명 인식**: 지역, 업종, 자금 규모 등 핵심 정보 추출
- **컨텍스트 구축**: 사용자 프로필과 질문을 결합한 검색 컨텍스트 생성

**입력/출력:**
```python
# 입력
{
    "query": "경기도에서 카페 창업하는데 운영자금 지원 정책 있나요?",
    "user_profile": { ... },
    "session_context": { ... }
}

# 출력
{
    "intent": "funding_recommendation",
    "entities": {
        "region": "경기도",
        "industry": "음식점업",
        "funding_type": "운영자금",
        "business_stage": "창업"
    },
    "search_context": {
        "filters": { ... },
        "boost_factors": { ... }
    }
}
```

### 3.2. Search Engine (검색 엔진)
KMRR 알고리즘을 구현하여 최적의 정책을 발굴한다.

**검색 단계:**
1. **사전 필터링**: KG 기반 자격 요건 필터링
2. **벡터 검색**: Milvus에서 의미적 유사 정책 검색
3. **지식 기반 재순위**: Neo4j 추론을 통한 최종 순위 결정

**핵심 알고리즘:**
```python
async def kmrr_search(query_context: QueryContext) -> List[PolicyRecommendation]:
    # Stage 1: KG-Informed Pre-filtering
    eligible_policies = await self.kg_service.get_eligible_policies(
        user_profile=query_context.user_profile,
        constraints=query_context.entities
    )
    
    # Stage 2: Vector Search with Filters
    vector_results = await self.vector_service.search(
        query_embedding=query_context.embedding,
        filter_expression=self._build_filter(eligible_policies),
        limit=50
    )
    
    # Stage 3: Knowledge-Modulated Re-ranking
    final_results = []
    for policy, similarity_score in vector_results:
        kg_facts = await self.kg_service.get_policy_facts(
            policy_id=policy.id,
            user_context=query_context
        )
        
        final_score = self._calculate_final_score(
            similarity_score=similarity_score,
            kg_facts=kg_facts,
            business_rules=await self.rule_engine.get_active_rules()
        )
        
        final_results.append(PolicyRecommendation(
            policy=policy,
            score=final_score,
            reasoning=kg_facts
        ))
    
    return sorted(final_results, key=lambda x: x.score, reverse=True)
```

### 3.3. Explainer (설명 생성기)
추천 결과에 대한 논리적 근거와 설명을 생성한다.

**설명 구성 요소:**
- **적합성 근거**: 왜 이 정책이 추천되었는가
- **자격 요건 매칭**: 사용자가 어떤 조건을 만족하는가
- **점수 분해**: 각 요소별 점수 기여도
- **주의사항**: 신청 시 고려해야 할 사항들

## 4. API 명세 (API Specification)

### 4.1. 추천 생성 API
```http
POST /api/v1/recommendations
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
    "session_id": "user123-sess456",
    "query": "경기도 카페 창업 운영자금 지원",
    "user_profile": { ... },
    "options": {
        "max_results": 10,
        "include_explanations": true,
        "sort_by": "relevance"
    }
}
```

**응답 예시:**
```json
{
    "success": true,
    "data": {
        "recommendations": [
            {
                "rank": 1,
                "policy": { ... },
                "score_breakdown": {
                    "final_score": 0.95,
                    "semantic_similarity": 0.88,
                    "kg_boost_factor": 1.08,
                    "rule_adjustments": 0.02
                },
                "explanation": {
                    "why_recommended": "귀하의 업종과 지역에 가장 적합한 정책입니다.",
                    "eligibility_match": { ... },
                    "evidence_snippet": "경기도 소재 음식점업 창업자 대상..."
                }
            }
        ],
        "search_metadata": {
            "total_policies_searched": 1247,
            "processing_time_ms": 245,
            "search_strategy": "hybrid_rag_kg"
        }
    }
}
```

### 4.2. 피드백 수집 API
```http
POST /api/v1/recommendations/{recommendation_id}/feedback
Content-Type: application/json

{
    "overall_rating": 4,
    "helpful_policies": ["policy_id_1"],
    "not_helpful_policies": ["policy_id_2"],
    "comments": "첫 번째 추천이 정확했습니다."
}
```

## 5. 데이터 모델 (Data Models)

### 5.1. 추천 요청 모델
```python
class RecommendationRequest(BaseModel):
    session_id: str
    query: str = Field(..., min_length=1, max_length=1000)
    user_profile: UserProfile
    options: Optional[SearchOptions] = None

class SearchOptions(BaseModel):
    max_results: int = Field(default=10, ge=1, le=50)
    include_explanations: bool = True
    sort_by: Literal["relevance", "amount", "deadline"] = "relevance"
    include_expired: bool = False
```

### 5.2. 추천 결과 모델
```python
class PolicyRecommendation(BaseModel):
    rank: int
    policy: PolicySummary
    score_breakdown: ScoreBreakdown
    explanation: RecommendationExplanation

class ScoreBreakdown(BaseModel):
    final_score: float = Field(..., ge=0, le=1)
    semantic_similarity: float
    kg_boost_factor: float
    rule_adjustments: float
    matched_rules: List[str]

class RecommendationExplanation(BaseModel):
    why_recommended: str
    evidence_snippet: str
    eligibility_match: Dict[str, str]
    potential_issues: Optional[List[str]] = None
```

## 6. 성능 요구사항 (Performance Requirements)

### 6.1. 응답 시간 목표
- **일반 추천**: 3초 이내 (95th percentile)
- **캐시된 결과**: 500ms 이내
- **복잡한 쿼리**: 5초 이내

### 6.2. 처리량 목표
- **동시 사용자**: 1,000명
- **시간당 추천 요청**: 10,000건
- **일일 추천 요청**: 100,000건

### 6.3. 정확도 목표
- **추천 정확도**: 85% 이상 (사용자 만족도 기준)
- **자격 요건 매칭**: 99% 이상
- **중복 추천 방지**: 100%

## 7. 모니터링 및 메트릭 (Monitoring & Metrics)

### 7.1. 비즈니스 메트릭
```python
# 추천 품질 메트릭
recommendation_accuracy = Gauge('recommendation_accuracy_rate')
user_satisfaction_score = Histogram('user_satisfaction_score')
policy_application_rate = Counter('policy_applications_from_recommendations')

# 사용자 행동 메트릭
query_complexity_distribution = Histogram('query_complexity_score')
session_duration = Histogram('recommendation_session_duration_seconds')
```

### 7.2. 기술적 메트릭
```python
# 성능 메트릭
recommendation_processing_time = Histogram('recommendation_processing_seconds')
vector_search_latency = Histogram('vector_search_latency_seconds')
kg_reasoning_time = Histogram('kg_reasoning_time_seconds')

# 시스템 상태 메트릭
active_recommendation_sessions = Gauge('active_recommendation_sessions')
cache_hit_rate = Gauge('recommendation_cache_hit_rate')
```

## 8. 에러 처리 및 복구 (Error Handling & Recovery)

### 8.1. 에러 분류
```python
class RecommendationError(Exception):
    pass

class QueryParsingError(RecommendationError):
    """사용자 쿼리 파싱 실패"""
    pass

class SearchEngineError(RecommendationError):
    """검색 엔진 오류"""
    pass

class ExplanationGenerationError(RecommendationError):
    """설명 생성 실패"""
    pass
```

### 8.2. 복구 전략
- **부분 실패 허용**: 설명 생성 실패 시에도 추천 결과는 반환
- **폴백 메커니즘**: 복잡한 추론 실패 시 단순 벡터 검색으로 폴백
- **캐시 활용**: 동일 쿼리에 대한 캐시된 결과 제공

## 9. 보안 고려사항 (Security Considerations)

### 9.1. 데이터 보호
- 사용자 쿼리 로깅 시 개인정보 마스킹
- 추천 이력의 암호화 저장
- 민감한 프로필 정보 해시화

### 9.2. 접근 제어
- JWT 토큰 기반 인증
- 사용자별 추천 이력 격리
- 관리자 전용 메트릭 접근 제한

---

**📋 관련 문서**
- [상호작용 AI 코어](../../02_CORE_COMPONENTS/02_INTERACTIVE_AI_CORE.md)
- [살아있는 게이트웨이](../../02_CORE_COMPONENTS/03_LIVING_GATEWAY.md)
- [API 명세서](../../03_DATA_MODELS_AND_APIS/API_CONTRACT.md)
- [데이터베이스 스키마](../../03_DATA_MODELS_AND_APIS/DATABASE_SCHEMA.md)