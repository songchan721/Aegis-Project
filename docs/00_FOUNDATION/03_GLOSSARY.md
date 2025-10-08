# 이지스(Aegis) 프로젝트 용어 사전

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-FND-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 프로젝트 핵심 용어 (Core Project Terms)

### A

**Aegis (이지스)**
- 그리스 신화의 제우스와 아테나의 방패에서 유래
- 본 프로젝트명으로, "소상공인을 보호하는 방패" 역할을 의미
- 완전한 보호와 지원을 상징

**API Gateway**
- 모든 클라이언트 요청의 단일 진입점
- 라우팅, 인증, 로드밸런싱, 모니터링 등을 담당
- Kong 또는 Istio Gateway 사용

### C

**CDC (Change Data Capture)**
- 데이터베이스의 변경사항을 실시간으로 캡처하는 기술
- Debezium을 사용하여 PostgreSQL → Kafka로 변경 이벤트 전송
- 이중 트랙 파이프라인의 핵심 구성요소

**Cold Path (콜드 패스)**
- 이중 트랙 파이프라인의 배치 처리 경로
- 데이터 일관성과 정확성을 보장하는 역할
- Apache Airflow를 통한 워크플로우 관리

### D

**Dual-Track Pipeline (이중 트랙 파이프라인)**
- 실시간 처리(Hot Path)와 배치 처리(Cold Path)를 결합한 데이터 파이프라인
- 데이터 무결성 원칙을 구현하는 핵심 아키텍처
- Lambda Architecture 패턴의 구현체

### E

**Event Sourcing**
- 상태 변경을 이벤트의 시퀀스로 저장하는 패턴
- Kafka를 통한 이벤트 스트리밍의 기반
- 시스템의 모든 변경사항을 추적 가능

### H

**Hot Path (핫 패스)**
- 이중 트랙 파이프라인의 실시간 처리 경로
- 사용자 요청에 즉시 응답하기 위한 빠른 처리 경로
- Kafka Streams를 통한 스트림 처리

**HNSW (Hierarchical Navigable Small World)**
- Milvus에서 사용하는 벡터 인덱싱 알고리즘
- 고차원 벡터 공간에서의 근사 최근접 이웃 검색
- 검색 속도와 정확도의 균형을 제공

### I

**Interactive AI Core (상호작용 AI 코어)**
- RAG와 KG가 상호작용하는 지능형 추론 엔진
- 단방향 검색이 아닌 양방향 상호작용을 통한 추론
- 이지스 4대 원칙 중 "지능형 검색" 원칙의 구현체

### K

**KG (Knowledge Graph)**
- 정책 간의 관계와 규칙을 그래프 형태로 표현
- Neo4j를 사용한 그래프 데이터베이스
- 논리적 추론과 복잡한 조건 처리를 담당

**KMRR (Knowledge-Modulated Retrieval and Re-ranking)**
- 지식 그래프가 벡터 검색 과정에 개입하는 알고리즘
- KG-Informed Pre-filtering + Knowledge-Modulated Re-ranking
- Interactive AI Core의 핵심 알고리즘

### L

**LIL (Language Intelligence Layer, 언어 지능 계층)**
- 외부 LLM을 시스템의 부품으로 제어하는 추상화 계층
- LLM 종속성을 제거하고 일관된 사용자 경험 제공
- Living Gateway의 핵심 구성요소

**Living Gateway (살아있는 게이트웨이)**
- 외부 LLM과의 통신을 관리하는 적응형 게이트웨이
- 자동 페일오버, 동적 라우팅, 응답 검증 기능
- 이지스 4대 원칙 중 "적응형 회복탄력성" 원칙의 구현체

### M

**MSA (Microservices Architecture)**
- 애플리케이션을 독립적인 서비스들로 분해하는 아키텍처 패턴
- 각 서비스는 독립적으로 배포, 확장, 관리 가능
- 이지스 시스템의 기본 아키텍처 패턴

**Milvus**
- 대규모 벡터 데이터 검색에 특화된 오픈소스 벡터 데이터베이스
- RAG 파이프라인의 벡터 저장소 역할
- HNSW 인덱싱을 통한 고성능 유사도 검색

### P

**Polyglot Persistence**
- 각 데이터의 특성에 맞는 최적의 데이터베이스를 사용하는 전략
- PostgreSQL(관계형), Neo4j(그래프), Milvus(벡터), Redis(캐시)
- 데이터 특성에 따른 최적화된 저장 및 검색

### R

**RAG (Retrieval-Augmented Generation)**
- 검색 기반 생성 모델
- 벡터 검색을 통해 관련 문서를 찾고 LLM이 답변 생성
- 이지스 시스템의 기본 AI 패러다임

**Rules as Data (규칙의 데이터화)**
- 비즈니스 로직을 코드가 아닌 데이터베이스에 저장
- 시스템 재배포 없이 규칙 변경 가능
- 이지스 4대 원칙 중 "외부화된 로직" 원칙의 구현

### S

**S.C.O.R.E. Framework**
- **S**pecificity (구체성): 명확한 입출력 정의
- **C**onsistency (일관성): 동일 입력에 동일 결과
- **O**bservability (관찰가능성): 모든 과정 추적 가능
- **R**eproducibility (재현가능성): 결과 재현 가능
- **E**xplainability (설명가능성): 판단 근거 명확 제시

**SSoT (Single Source of Truth)**
- 단일 진실 공급원
- PostgreSQL이 시스템의 모든 데이터에 대한 SSoT 역할
- 데이터 일관성과 무결성의 기준점

### V

**Vector Embedding**
- 텍스트를 고차원 벡터로 변환한 표현
- 의미적 유사성을 수치적으로 계산 가능
- RAG 시스템의 검색 기반

## 2. 기술 용어 (Technical Terms)

### 데이터베이스 관련

**ACID**
- **A**tomicity (원자성): 트랜잭션의 모든 연산이 완전히 수행되거나 전혀 수행되지 않음
- **C**onsistency (일관성): 트랜잭션 실행 후에도 데이터베이스가 일관된 상태 유지
- **I**solation (격리성): 동시 실행되는 트랜잭션들이 서로 영향을 주지 않음
- **D**urability (지속성): 성공적으로 완료된 트랜잭션의 결과는 영구적으로 반영

**JSONB**
- PostgreSQL의 바이너리 JSON 데이터 타입
- JSON보다 빠른 검색과 인덱싱 지원
- 메타데이터 저장에 활용

**GIN Index**
- Generalized Inverted Index
- PostgreSQL에서 배열, JSONB 등의 복합 데이터 타입 인덱싱
- 빠른 포함 관계 검색 지원

### 메시징 및 스트리밍

**Apache Kafka**
- 분산 스트리밍 플랫폼
- 높은 처리량과 내결함성을 가진 메시지 큐
- 이벤트 소싱과 CQRS 패턴의 기반

**Kafka Streams**
- Kafka 기반의 스트림 처리 라이브러리
- 실시간 데이터 변환과 집계 처리
- Hot Path 구현에 활용

**Topic**
- Kafka에서 메시지가 저장되는 논리적 채널
- 파티션으로 분할되어 병렬 처리 지원
- 이벤트 타입별로 토픽 분리

### 컨테이너 및 오케스트레이션

**Docker**
- 컨테이너 기반 가상화 플랫폼
- 애플리케이션과 의존성을 패키징
- 일관된 실행 환경 제공

**Kubernetes (K8s)**
- 컨테이너 오케스트레이션 플랫폼
- 자동 배포, 스케일링, 관리 기능
- 클라우드 네이티브 애플리케이션의 표준

**Helm**
- Kubernetes 패키지 매니저
- 복잡한 애플리케이션의 배포 템플릿화
- 버전 관리와 롤백 지원

**Istio**
- 서비스 메시 플랫폼
- 마이크로서비스 간 통신 관리
- 보안, 모니터링, 트래픽 관리 기능

### AI/ML 관련

**Embedding Model**
- 텍스트를 벡터로 변환하는 모델
- sentence-transformers, OpenAI embeddings 등
- 의미적 유사성 계산의 기반

**Vector Similarity**
- 벡터 간의 유사도 측정 방법
- L2 Distance, Cosine Similarity, Inner Product
- 검색 결과의 관련성 판단 기준

**Fine-tuning**
- 사전 훈련된 모델을 특정 도메인에 맞게 추가 학습
- 도메인 특화 성능 향상
- 정책 도메인 특화 모델 개발에 활용

## 3. 비즈니스 도메인 용어 (Business Domain Terms)

### 정책자금 관련

**소상공인**
- 상시근로자 수 10명 미만 또는 연매출 10억원 미만의 사업자
- 정책자금의 주요 대상
- 업종별로 세부 기준 상이

**정책자금**
- 정부나 지방자치단체에서 특정 목적으로 지원하는 자금
- 창업자금, 운영자금, 시설자금 등으로 분류
- 저금리 대출, 보조금, 융자 등 다양한 형태

**중복수혜**
- 동일한 목적으로 여러 정책자금을 동시에 받는 것
- 대부분의 정책에서 제한하는 조건
- Knowledge Graph로 관계 모델링

### 추천 시스템 관련

**개인화 (Personalization)**
- 사용자의 특성과 상황에 맞춘 맞춤형 추천
- 사용자 프로필 기반 필터링과 랭킹
- 추천 시스템의 핵심 가치

**설명가능성 (Explainability)**
- AI의 판단 근거를 사용자가 이해할 수 있도록 설명
- S.C.O.R.E. 프레임워크의 핵심 요소
- 신뢰성 있는 AI 서비스의 필수 조건

**콜드 스타트 (Cold Start)**
- 신규 사용자나 신규 아이템에 대한 추천 문제
- 프로필 정보와 규칙 기반 추천으로 해결
- 점진적 학습을 통한 개선

## 4. 운영 및 모니터링 용어 (Operations & Monitoring Terms)

### 모니터링

**SLA (Service Level Agreement)**
- 서비스 수준 협약
- 가용성, 응답시간 등의 서비스 품질 기준
- 99.9% 가용성, 3초 이내 응답시간 등

**SLI (Service Level Indicator)**
- 서비스 수준 지표
- SLA 달성 여부를 측정하는 구체적 메트릭
- 응답시간, 에러율, 처리량 등

**SLO (Service Level Objective)**
- 서비스 수준 목표
- SLI의 목표값 설정
- SLA 달성을 위한 내부 목표

### 보안

**JWT (JSON Web Token)**
- 사용자 인증을 위한 토큰 기반 인증 방식
- 상태를 저장하지 않는 무상태 인증
- API 보안의 표준 방식

**RBAC (Role-Based Access Control)**
- 역할 기반 접근 제어
- 사용자의 역할에 따른 권한 관리
- 관리자, 일반사용자 등 역할별 접근 제어

**mTLS (Mutual TLS)**
- 상호 TLS 인증
- 클라이언트와 서버가 서로를 인증
- 마이크로서비스 간 보안 통신

## 5. 성능 및 확장성 용어 (Performance & Scalability Terms)

**Horizontal Scaling (수평 확장)**
- 서버 인스턴스 수를 늘려 처리 능력 향상
- Kubernetes의 Pod 복제를 통한 확장
- 마이크로서비스 아키텍처의 장점

**Vertical Scaling (수직 확장)**
- 단일 서버의 CPU, 메모리 등을 증가
- 확장 한계가 있지만 구현이 간단
- 데이터베이스 등에서 주로 사용

**Circuit Breaker**
- 장애 전파를 방지하는 패턴
- 외부 서비스 장애 시 빠른 실패 처리
- Living Gateway에서 구현

**Bulkhead Pattern**
- 시스템 자원을 격리하여 장애 영향 최소화
- 선박의 격벽에서 유래한 패턴
- 마이크로서비스별 자원 격리

## 6. 약어 및 축약어 (Abbreviations & Acronyms)

| 약어 | 전체 명칭 | 한글 의미 |
|------|-----------|-----------|
| **AI** | Artificial Intelligence | 인공지능 |
| **API** | Application Programming Interface | 애플리케이션 프로그래밍 인터페이스 |
| **CDC** | Change Data Capture | 변경 데이터 캡처 |
| **CQRS** | Command Query Responsibility Segregation | 명령 쿼리 책임 분리 |
| **ETL** | Extract, Transform, Load | 추출, 변환, 적재 |
| **GDPR** | General Data Protection Regulation | 일반 데이터 보호 규정 |
| **HNSW** | Hierarchical Navigable Small World | 계층적 탐색 가능한 소세계 |
| **JWT** | JSON Web Token | JSON 웹 토큰 |
| **KG** | Knowledge Graph | 지식 그래프 |
| **KMRR** | Knowledge-Modulated Retrieval and Re-ranking | 지식 조절 검색 및 재순위 |
| **LIL** | Language Intelligence Layer | 언어 지능 계층 |
| **LLM** | Large Language Model | 대규모 언어 모델 |
| **MSA** | Microservices Architecture | 마이크로서비스 아키텍처 |
| **NLP** | Natural Language Processing | 자연어 처리 |
| **RBAC** | Role-Based Access Control | 역할 기반 접근 제어 |
| **RAG** | Retrieval-Augmented Generation | 검색 증강 생성 |
| **SLA** | Service Level Agreement | 서비스 수준 협약 |
| **SLI** | Service Level Indicator | 서비스 수준 지표 |
| **SLO** | Service Level Objective | 서비스 수준 목표 |
| **SSoT** | Single Source of Truth | 단일 진실 공급원 |

---

**📋 관련 문서**
- [프로젝트 헌장](./00_CHARTER.md)
- [프로젝트 구조](./00_PROJECT_STRUCTURE.md)
- [Spec 분할 전략](./02_SPEC_STRATEGY.md)