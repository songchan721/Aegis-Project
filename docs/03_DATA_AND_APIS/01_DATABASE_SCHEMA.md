# 이지스(Aegis) 통합 데이터베이스 스키마

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-API-20250917-1.0 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 '이지스(Aegis)' 시스템을 구성하는 모든 데이터베이스의 논리적, 물리적 스키마를 정의한다. 이 문서는 시스템의 모든 데이터 구조에 대한 **단일 진실 공급원(Single Source of Truth)**이며, 모든 백엔드 및 데이터 엔지니어링 작업은 본 문서의 정의를 따라야 한다.

## 2. 데이터베이스 아키텍처 개요

### 2.1. 다중 데이터베이스 전략
이지스 시스템은 **Polyglot Persistence** 패턴을 채택하여 각 데이터의 특성에 최적화된 데이터베이스를 사용합니다.

| 데이터베이스 | 타입 | 주 역할 | 주요 저장 데이터 |
|-------------|------|---------|------------------|
| **PostgreSQL** | RDBMS | 시스템의 메인 DB, 단일 진실 공급원 | 정책 원문, 메타데이터, 사용자 정보, 규칙, 모델 목록, 상태 관리 |
| **Milvus** | Vector DB | 의미 기반 검색 (RAG의 'R') | 정책 문서의 임베딩 벡터 및 필터링용 메타데이터 |
| **Neo4j** | Graph DB | 논리적 추론 (KG) | 정책 간 관계, 자격 요건 등의 지식 그래프 |
| **Redis** | In-Memory | 캐싱 및 세션 관리 | API 응답 캐시, 사용자 세션, 임시 데이터 |

### 2.2. 데이터 일관성 전략
- **PostgreSQL**: 강한 일관성 (Strong Consistency) - ACID 트랜잭션
- **Milvus/Neo4j**: 최종적 일관성 (Eventual Consistency) - 이중 트랙 파이프라인으로 동기화
- **Redis**: 캐시 무효화 전략으로 일관성 보장

## 3. PostgreSQL 스키마 (Primary Database)

### 3.1. 핵심 테이블 구조

#### 3.1.1. 정책자금 테이블 (policies)
```sql
CREATE TABLE policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 기본 정보
    title VARCHAR(512) NOT NULL,
    issuing_organization VARCHAR(255) NOT NULL,
    original_text TEXT NOT NULL,
    summary TEXT,
    
    -- 메타데이터 (JSONB로 유연성 확보)
    metadata JSONB NOT NULL DEFAULT '{}',
    
    -- 자격 요건 및 조건
    eligibility_criteria JSONB DEFAULT '[]',
    funding_details JSONB DEFAULT '{}',
    
    -- 대상 정보
    target_regions TEXT[] DEFAULT '{}',
    target_industries TEXT[] DEFAULT '{}',
    target_business_types TEXT[] DEFAULT '{}',
    
    -- 기간 정보
    application_start_date DATE,
    application_end_date DATE,
    
    -- 원본 정보
    original_url VARCHAR(2048),
    source_system VARCHAR(100),
    
    -- 시스템 관리
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 인덱스
    CONSTRAINT policies_title_check CHECK (length(title) > 0),
    CONSTRAINT policies_org_check CHECK (length(issuing_organization) > 0)
);

-- 인덱스 생성
CREATE INDEX idx_policies_active ON policies (is_active) WHERE is_active = true;
CREATE INDEX idx_policies_regions ON policies USING GIN (target_regions);
CREATE INDEX idx_policies_industries ON policies USING GIN (target_industries);
CREATE INDEX idx_policies_metadata ON policies USING GIN (metadata);
CREATE INDEX idx_policies_application_period ON policies (application_start_date, application_end_date);
```

#### 3.1.2. 사용자 테이블 (users)
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 인증 정보
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    
    -- 프로필 정보 (AI 추천에 사용)
    profile JSONB NOT NULL DEFAULT '{}',
    
    -- 사용자 상태
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    
    -- 시스템 관리
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- 인덱스
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_active ON users (is_active) WHERE is_active = true;
```

#### 3.1.3. 사용자 프로필 스키마 (JSONB)
```json
{
  "business_info": {
    "business_type": "소상공인|중소기업|개인사업자",
    "industry_code": "한국표준산업분류코드",
    "industry_name": "업종명",
    "business_scale": "매출규모|직원수",
    "establishment_date": "2023-01-15",
    "business_registration_number": "해시된값"
  },
  "location": {
    "region_code": "지역코드",
    "region_name": "서울특별시 강남구",
    "detailed_address": "해시된값"
  },
  "financial_info": {
    "annual_revenue": 100000000,
    "employee_count": 5,
    "current_funding": ["기존수혜정책ID1", "기존수혜정책ID2"]
  },
  "preferences": {
    "funding_purpose": ["운영자금", "시설자금", "창업자금"],
    "preferred_amount_range": [10000000, 50000000],
    "max_interest_rate": 3.5
  }
}
```

#### 3.1.4. 추천 이력 테이블 (recommendation_history)
```sql
CREATE TABLE recommendation_history (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    
    -- 요청 정보
    query_text TEXT NOT NULL,
    user_profile_snapshot JSONB NOT NULL,
    
    -- 추천 결과
    recommended_policies JSONB NOT NULL, -- 정책 ID와 점수 배열
    
    -- S.C.O.R.E. 프레임워크 메트릭
    score_metrics JSONB NOT NULL DEFAULT '{}',
    
    -- 사용자 피드백
    user_feedback JSONB DEFAULT '{}',
    
    -- 시스템 정보
    model_version VARCHAR(50),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_recommendation_user ON recommendation_history (user_id);
CREATE INDEX idx_recommendation_created ON recommendation_history (created_at);
```

#### 3.1.5. 규칙 엔진 테이블 (business_rules)
```sql
CREATE TABLE business_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 규칙 정보
    rule_name VARCHAR(255) NOT NULL UNIQUE,
    rule_type VARCHAR(50) NOT NULL, -- 'scoring', 'filtering', 'boosting'
    
    -- 규칙 정의 (JSON으로 유연성 확보)
    rule_definition JSONB NOT NULL,
    
    -- 적용 조건
    conditions JSONB DEFAULT '{}',
    
    -- 가중치 및 파라미터
    weight DECIMAL(5,4) DEFAULT 1.0,
    parameters JSONB DEFAULT '{}',
    
    -- 상태 관리
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,
    
    -- 메타데이터
    description TEXT,
    created_by VARCHAR(255),
    
    -- 시스템 관리
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT rules_weight_check CHECK (weight >= 0 AND weight <= 10)
);

-- 인덱스
CREATE INDEX idx_rules_active ON business_rules (is_active, priority) WHERE is_active = true;
CREATE INDEX idx_rules_type ON business_rules (rule_type);
```

### 3.2. 데이터 무결성 제약조건

#### 3.2.1. 외래키 제약조건
```sql
-- 추천 이력과 사용자 연결
ALTER TABLE recommendation_history 
ADD CONSTRAINT fk_recommendation_user 
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
```

#### 3.2.2. 체크 제약조건
```sql
-- 정책 메타데이터 필수 필드 검증
ALTER TABLE policies 
ADD CONSTRAINT check_metadata_required 
CHECK (metadata ? 'data_source' AND metadata ? 'last_verified');

-- 사용자 프로필 필수 필드 검증
ALTER TABLE users 
ADD CONSTRAINT check_profile_business_type 
CHECK (profile ? 'business_info');
```

## 4. Milvus 스키마 (Vector Database)

### 4.1. Collection 정의

#### Collection Name: `aegis_policies_v1`

```python
# Milvus Collection Schema
from pymilvus import CollectionSchema, FieldSchema, DataType

fields = [
    FieldSchema(name="policy_pk", dtype=DataType.INT64, is_primary=True, auto_id=False),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    
    # 사전 필터링용 메타데이터
    FieldSchema(name="region_codes", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="industry_codes", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="business_types", dtype=DataType.VARCHAR, max_length=200),
    FieldSchema(name="funding_amount_min", dtype=DataType.INT64),
    FieldSchema(name="funding_amount_max", dtype=DataType.INT64),
    FieldSchema(name="is_active", dtype=DataType.BOOL),
    
    # 검색 성능 최적화용
    FieldSchema(name="text_length", dtype=DataType.INT32),
    FieldSchema(name="last_updated", dtype=DataType.INT64)  # Unix timestamp
]

schema = CollectionSchema(fields, "Aegis Policy Embeddings for RAG Search")
```

### 4.2. 인덱스 전략

```python
# HNSW 인덱스 설정
index_params = {
    "metric_type": "L2",
    "index_type": "HNSW",
    "params": {
        "M": 16,              # 연결 수 (메모리 vs 성능 트레이드오프)
        "efConstruction": 64  # 구축 시 탐색 깊이
    }
}

# 검색 파라미터
search_params = {
    "metric_type": "L2",
    "params": {
        "ef": 32  # 검색 시 탐색 깊이 (정확도 vs 속도)
    }
}
```

### 4.3. 파티션 전략
```python
# 지역별 파티션으로 검색 성능 최적화
partitions = [
    "seoul",      # 서울특별시
    "gyeonggi",   # 경기도
    "busan",      # 부산광역시
    "national",   # 전국 대상
    "others"      # 기타 지역
]
```

## 5. Neo4j 스키마 (Knowledge Graph)

### 5.1. 노드 레이블 정의

#### 5.1.1. Policy 노드
```cypher
CREATE CONSTRAINT policy_id_unique IF NOT EXISTS 
FOR (p:Policy) REQUIRE p.id IS UNIQUE;

// Policy 노드 예시
(:Policy {
  id: "uuid-string",
  title: "정책명",
  organization: "발행기관",
  category: "창업지원|운영자금|시설자금",
  status: "active|inactive|expired"
})
```

#### 5.1.2. Requirement 노드
```cypher
(:Requirement {
  type: "age|revenue|employee_count|region|industry",
  operator: ">=|<=|=|in|not_in",
  value: "조건값",
  unit: "years|won|people|code"
})
```

#### 5.1.3. Entity 노드들
```cypher
(:Region {code: "11", name: "서울특별시"})
(:Industry {code: "56", name: "음식점업"})
(:BusinessType {code: "small", name: "소상공인"})
(:Organization {name: "중소벤처기업부", type: "central_gov"})
```

### 5.2. 관계 타입 정의

```cypher
// 정책 자격 요건
(:Policy)-[:HAS_REQUIREMENT]->(:Requirement)

// 정책 대상
(:Policy)-[:TARGETS_REGION]->(:Region)
(:Policy)-[:TARGETS_INDUSTRY]->(:Industry)
(:Policy)-[:TARGETS_BUSINESS_TYPE]->(:BusinessType)

// 정책 발행
(:Organization)-[:ISSUES]->(:Policy)

// 정책 간 관계
(:Policy)-[:CONFLICTS_WITH]->(:Policy)  // 중복 수혜 불가
(:Policy)-[:COMPLEMENTS]->(:Policy)     // 함께 수혜 가능
(:Policy)-[:PREREQUISITE_FOR]->(:Policy) // 선행 조건

// 요건 간 관계
(:Requirement)-[:AND]->(:Requirement)
(:Requirement)-[:OR]->(:Requirement)
```

### 5.3. 추론 쿼리 예시

#### 사용자 적격성 검사
```cypher
MATCH (p:Policy)-[:HAS_REQUIREMENT]->(r:Requirement)
WHERE p.id = $policy_id
WITH p, collect(r) as requirements
RETURN p, requirements,
  reduce(eligible = true, req IN requirements | 
    eligible AND checkEligibility(req, $user_profile)
  ) as is_eligible
```

## 6. Redis 스키마 (Caching Layer)

### 6.1. 키 네이밍 컨벤션
```
aegis:{environment}:{data_type}:{identifier}

예시:
- aegis:prod:search:hash_of_query_and_profile
- aegis:prod:policy:uuid
- aegis:prod:user_session:user_id
- aegis:prod:recommendation:user_id:timestamp
```

### 6.2. 캐시 전략
| 데이터 타입 | TTL | 캐시 키 패턴 | 설명 |
|------------|-----|-------------|------|
| 검색 결과 | 1시간 | `search:{query_hash}` | 동일 쿼리 재검색 방지 |
| 정책 상세 | 24시간 | `policy:{policy_id}` | 정책 상세 정보 캐시 |
| 사용자 세션 | 30분 | `session:{session_id}` | 사용자 세션 관리 |
| 추천 결과 | 6시간 | `rec:{user_id}:{profile_hash}` | 개인화 추천 캐시 |

## 7. 데이터 마이그레이션 및 버전 관리

### 7.1. 스키마 버전 관리
```sql
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    checksum VARCHAR(64) NOT NULL
);
```

### 7.2. 데이터 동기화 전략
- **PostgreSQL → Milvus**: CDC (Change Data Capture) via Debezium
- **PostgreSQL → Neo4j**: 배치 ETL via Apache Airflow
- **Cache Invalidation**: 이벤트 기반 무효화

---

**📋 관련 문서**
- [API 명세서](./API_CONTRACT.md)
- [시스템 아키텍처](../01_SYSTEM_ARCHITECTURE.md)
- [이중 트랙 파이프라인](../02_CORE_COMPONENTS/01_DUAL_TRACK_PIPELINE.md)