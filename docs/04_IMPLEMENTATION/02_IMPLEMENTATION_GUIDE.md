# 이지스(Aegis) 구현 계획서
**Phase 1: MVP 구현 상세 가이드**

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-IMP-20250917-2.0 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 구현 철학 (Implementation Philosophy)

### 1.1. S.C.O.R.E. 프레임워크 기반 개발
모든 구현은 **S.C.O.R.E. 프레임워크**를 따라 정량적으로 측정 가능하고 감사 가능해야 합니다.

- **S**pecificity (구체성): 모든 기능은 명확한 입력과 출력을 정의
- **C**onsistency (일관성): 동일한 입력에 대해 항상 동일한 결과 보장
- **O**bservability (관찰가능성): 모든 처리 과정을 로깅하고 추적 가능
- **R**eproducibility (재현가능성): 모든 결과를 재현할 수 있는 환경 제공
- **E**xplainability (설명가능성): 모든 판단의 근거를 명확히 제시

### 1.2. 언어 지능 계층(LIL) 설계 원칙
외부 LLM에 종속되지 않는 **Language Intelligence Layer**를 구축하여:
- LLM을 시스템의 '부품'으로 완전히 제어
- 모든 LLM 응답을 내부 로직으로 검증 및 후처리
- LLM 교체 시에도 사용자 경험의 일관성 보장

## 2. Phase 1 구현 로드맵 (3개월)

### Sprint 1: 기반 인프라 구축 (Week 1-2)
#### 목표: 개발 환경 및 기본 데이터 파이프라인 구축

**Week 1: 프로젝트 초기화**
```bash
# 프로젝트 구조
aegis-mvp/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── core/           # 핵심 설정 및 유틸리티
│   │   ├── models/         # 데이터 모델
│   │   ├── api/            # API 라우터
│   │   ├── services/       # 비즈니스 로직
│   │   └── db/             # 데이터베이스 관련
│   ├── tests/              # 테스트 코드
│   └── requirements.txt
├── frontend/               # React 프론트엔드
├── data/                   # 데이터 수집 스크립트
├── docker/                 # Docker 설정
└── docs/                   # 문서
```

**핵심 작업:**
1. FastAPI 프로젝트 초기화
2. PostgreSQL + Redis Docker 설정
3. 기본 CI/CD 파이프라인 구축
4. 개발 환경 문서화

**Week 2: 데이터 수집 시스템**
1. 정부 정책자금 데이터 소스 조사
2. 웹 크롤링 스크립트 개발
3. 데이터 정제 및 표준화 로직
4. PostgreSQL 스키마 구현

### Sprint 2: 핵심 RAG 파이프라인 (Week 3-4)
#### 목표: 기본적인 벡터 검색 시스템 구현

**Week 3: 벡터화 및 저장**
1. 텍스트 임베딩 생성 파이프라인
   ```python
   # 예시 구조
   class EmbeddingService:
       def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
           self.model = SentenceTransformer(model_name)
       
       def generate_embeddings(self, texts: List[str]) -> np.ndarray:
           return self.model.encode(texts)
   ```

2. Milvus 연동 및 벡터 저장
3. 데이터 동기화 로직 구현

**Week 4: 검색 및 매칭**
1. 유사도 기반 검색 API
2. 기본적인 사용자 프로필 매칭
3. 결과 랭킹 알고리즘 (Phase 1 버전)

### Sprint 3: API 및 비즈니스 로직 (Week 5-6)
#### 목표: 완전한 백엔드 API 구현

**핵심 API 엔드포인트:**
```python
# API 구조 예시
@router.post("/search")
async def search_policies(query: SearchQuery) -> SearchResponse:
    """자연어 쿼리로 정책자금 검색"""
    pass

@router.post("/recommend")
async def recommend_policies(profile: UserProfile) -> RecommendationResponse:
    """사용자 프로필 기반 추천"""
    pass

@router.get("/policies/{policy_id}")
async def get_policy_detail(policy_id: str) -> PolicyDetail:
    """정책 상세 정보 조회"""
    pass
```

### Sprint 4: 프론트엔드 및 통합 (Week 7-8)
#### 목표: 사용자 인터페이스 구현 및 전체 시스템 통합

**Week 7: React 프론트엔드**
1. 검색 인터페이스 구현
2. 결과 표시 컴포넌트
3. 사용자 프로필 관리

**Week 8: 통합 및 테스트**
1. 전체 시스템 통합 테스트
2. 성능 최적화
3. 사용자 피드백 수집 시스템

### Sprint 5: 최적화 및 배포 (Week 9-12)
#### 목표: 성능 최적화 및 프로덕션 배포

**핵심 작업:**
1. 캐싱 전략 구현 (Redis)
2. 데이터베이스 인덱싱 최적화
3. API 응답 시간 최적화
4. 모니터링 및 로깅 시스템
5. 보안 강화
6. 프로덕션 배포

## 3. 기술 구현 상세

### 3.1. 데이터 모델 설계

#### 핵심 엔티티
```python
# 정책자금 모델
class Policy(BaseModel):
    id: str
    title: str
    description: str
    eligibility_criteria: List[str]
    funding_amount: Optional[str]
    interest_rate: Optional[float]
    application_period: DateRange
    target_business_type: List[str]
    target_region: List[str]
    source_organization: str
    created_at: datetime
    updated_at: datetime

# 사용자 프로필 모델
class UserProfile(BaseModel):
    business_type: str
    business_scale: str  # 소상공인, 중소기업 등
    region: str
    annual_revenue: Optional[int]
    employee_count: Optional[int]
    establishment_date: Optional[date]
    current_funding_status: List[str]
```

### 3.2. RAG 파이프라인 구현

#### 검색 프로세스
```python
class RAGSearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_db = MilvusClient()
        self.policy_db = PolicyRepository()
    
    async def search(self, query: str, user_profile: UserProfile) -> List[Policy]:
        # 1. 쿼리 임베딩 생성
        query_embedding = self.embedding_service.generate_embeddings([query])[0]
        
        # 2. 벡터 유사도 검색
        similar_policies = await self.vector_db.search(
            query_embedding, 
            top_k=50
        )
        
        # 3. 사용자 프로필 기반 필터링
        filtered_policies = self.filter_by_profile(similar_policies, user_profile)
        
        # 4. 랭킹 및 재정렬
        ranked_policies = self.rank_policies(filtered_policies, query, user_profile)
        
        return ranked_policies[:10]
```

### 3.3. 언어 지능 계층(LIL) 구현

#### LLM 추상화 계층
```python
class LanguageIntelligenceLayer:
    def __init__(self):
        self.primary_llm = OpenAIClient()
        self.fallback_llm = HuggingFaceClient()
        self.response_validator = ResponseValidator()
    
    async def process_query(self, user_input: str) -> ProcessedQuery:
        """사용자 입력을 구조화된 쿼리로 변환"""
        try:
            # Primary LLM 시도
            response = await self.primary_llm.process(user_input)
            
            # 응답 검증
            if self.response_validator.is_valid(response):
                return self.parse_response(response)
            else:
                # Fallback LLM 사용
                return await self.fallback_process(user_input)
                
        except Exception as e:
            # 완전 실패 시 규칙 기반 처리
            return self.rule_based_fallback(user_input)
```

## 4. 품질 보증 전략

### 4.1. 테스트 전략
```python
# 단위 테스트 예시
class TestRAGSearchService:
    def test_search_accuracy(self):
        """검색 정확도 테스트"""
        test_cases = [
            ("소상공인 창업자금", ["창업지원금", "소상공인정책자금"]),
            ("제조업 운영자금", ["제조업지원금", "운영자금대출"])
        ]
        
        for query, expected_categories in test_cases:
            results = self.search_service.search(query, self.sample_profile)
            assert self.check_relevance(results, expected_categories)
```

### 4.2. 성능 모니터링
```python
# 성능 메트릭 수집
class PerformanceMonitor:
    def __init__(self):
        self.metrics = MetricsCollector()
    
    @monitor_performance
    async def track_search_performance(self, query: str):
        start_time = time.time()
        
        # 검색 실행
        results = await self.search_service.search(query)
        
        # 메트릭 기록
        self.metrics.record({
            'search_latency': time.time() - start_time,
            'result_count': len(results),
            'query_length': len(query)
        })
```

## 5. 배포 및 운영

### 5.1. Docker 컨테이너화
```dockerfile
# Dockerfile 예시
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2. 환경 설정
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aegis
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
      - milvus

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: aegis
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass

  redis:
    image: redis:7-alpine

  milvus:
    image: milvusdb/milvus:latest
```

## 6. 다음 단계 준비

### Phase 2 준비사항
1. **Knowledge Graph 설계**: Neo4j 스키마 계획
2. **KMRR 알고리즘 연구**: 논문 및 구현 방법 조사
3. **S.C.O.R.E. 프레임워크 구체화**: 정량적 지표 정의

---

**📋 관련 문서**
- [마스터플랜](./01_MASTERPLAN.md)
- [데이터베이스 스키마](../03_DATA_MODELS_AND_APIS/DATABASE_SCHEMA.md)
- [API 명세서](../03_DATA_MODELS_AND_APIS/API_CONTRACT.md)
- [설계 가이드라인](../DESIGN_GUIDELINES.md)