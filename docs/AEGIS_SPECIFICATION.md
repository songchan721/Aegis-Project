이지스(Aegis) 아키텍처 명세서 (Aegis Architecture Specification)
항목

내용

문서 ID

AAS-20250917-1.1

버전

1.1 (운영 아키텍처 포함)

최종 수정일

2025년 9월 17일

저자

Dr. Aiden (수석 AI 시스템 아키텍트), Jamie (품질 아키텍트)

상태

공식 승인 (Officially Approved)

1. 프로젝트 헌장 (Project Charter)
1.1. 미션과 비전 (Mission & Vision)
미션 (Mission): 기술의 장벽을 넘어, 모든 소상공인이 자신에게 맞는 최적의 정책자금 기회를 발견하고 성공적으로 확보할 수 있도록 돕는 지능형 파트너가 된다.

비전 (Vision): 단순 정보 검색 시스템을 넘어, 사용자의 상황을 깊이 이해하고, 신뢰할 수 있는 정보를 바탕으로 논리적인 추론을 통해 최적의 대안을 '증명'하고 '설명'할 수 있는 대한민국 최고의 정책자금 AI 에이전트를 구축한다.

1.2. 핵심 원칙: 이지스(Aegis) 4대 원칙
본 시스템의 모든 설계와 구현은 아래의 4대 핵심 원칙이라는 불변의 헌법을 따른다. 이 원칙들은 시스템의 기능적, 운영적 완벽성을 보장하는 대전제이다.

데이터 무결성: '이중 트랙(Dual-Track)' 원칙

철학: 데이터의 일관성은 타협의 대상이 아니다. 실시간성과 최종적 일관성, 두 가지 상충하는 목표를 모두 달성하여 그 어떤 순간에도 사용자에게는 완벽하게 정합성이 맞는 데이터만을 제공한다.

지능형 검색: '상호작용 AI 코어(Interactive AI Core)' 원칙

철학: 지능은 단방향으로 흐르지 않는다. 검색(Retrieval)과 추론(Reasoning)은 서로를 보완하고 강화하는 상호작용을 통해, 단순한 '유사 문서'가 아닌 '논리적으로 검증된 정답'을 찾아낸다.

적응형 회복탄력성: '살아있는 게이트웨이(Living Gateway)' 원칙

철학: 외부 환경의 불확실성은 시스템 내부로 전파되어서는 안 된다. 외부 의존성은 능동적인 방어벽을 통해 기술적 장애를 넘어 의미적, 경험적 일관성까지 완벽하게 통제되어야 한다.

외부화된 로직: '규칙은 코드가 아닌 데이터(Rules as Data)' 원칙

철학: 시스템은 살아있는 유기체와 같다. 재배포 없이 스스로 행동을 수정하고, 데이터 기반으로 최적화하며 환경 변화에 끊임없이 적응하고 진화해야 한다.

🗎 상세 문서: ./00_CHARTER.md

2. 통합 시스템 아키텍처 (System Architecture Overview)
2.1. 전체 다이어그램 (Master Diagram)
+--------------------------------------------------------------------------------------------------+
|                                     [ User / Client ]                                            |
+------------------------------------------+-------------------------------------------------------+
                                           | (REST API Request)
                                           v
+--------------------------------------+---+-------------------------------------------------------+
|  [ Application Layer ]               |   [ AI Core Layer ] - Interactive AI Core                 |
|                                      |                                                           |
|  +--------------------------------+  |   +----------------------------------------------------+  |
|  |       Backend (FastAPI)        |----&gt; |  Living Gateway (LLM Gateway)                      |  |
|  +--------------------------------+  |   +--------------------------+-------------------------+  |
|               ^                      |                              |                                   |
|               | (Cache)              |                              v                                   |
|  +--------------------------------+  |   +----------------------------------------------------+  |
|  |    Cache (Redis)               |  |   |         RAG-KG Hybrid Engine (KMRR)                |  |
|  +--------------------------------+  |   | - KG-Informed Pre-filtering                        |  |
+--------------------------------------+   | - Knowledge-Modulated Re-ranking                   |  |
                                       |   +--------------------------+-------------------------+  |
+--------------------------------------+------------------------------|---------------------------+
         ^ (Hot Path Event)            |                              | (Data Retrieval)
         |                             |                              v
+--------+-----------------------------+------------------------------+---------------------------+
|  [ Data Layer ]                      |  [ Message Queue (Kafka) ]   |                           |
|  +------------------------+          |   - Real-time Data Events    |  +------------------------+ |
|  |   Vector DB (Milvus)   |          +------------------------------+  |  Graph DB (Neo4j)      | |
|  +------------------------+                                            +------------------------+ |
|  +-------------------------------+                                                               |
|  |  RDBMS (PostgreSQL)           | &lt;----(CDC: Debezium)                                           |
|  | - Master State & Raw Data     |                                                               |
|  +-------------------------------+                                                               |
+--------------------------------------------------^-----------------------------------------------+
                                                   | (Processed Data - Cold Path)
                                                   |
+--------------------------------------------------+-----------------------------------------------+
|  [ Data Pipeline Layer ] - Dual-Track Pipeline                                                   |
|  - Hot Path: Event Consumers (Kafka Streams / Python)                                            |
|  - Cold Path: Workflow Orchestrator (Apache Airflow)                                             |
+--------------------------------------------------+-----------------------------------------------+
                                                   | (Deploy, Scale, Manage)
                                                   v
+--------------------------------------------------------------------------------------------------+
|  [ Infrastructure & Orchestration Layer ]                                                        |
|  - All components are containerized via Docker                                                   |
|  - Orchestrated by Kubernetes (K8s)                                                              |
+--------------------------------------------------------------------------------------------------+

2.2. 기술 스택 및 선정 사유 요약
계층

컴포넌트

기술 스택

핵심 선정 사유

Application

Backend API

FastAPI

Non-blocking I/O 기반의 극대화된 비동기 처리 성능



Cache

Redis

고성능 In-Memory 저장소, 캐시 및 세션 관리

AI Core

LLM Gateway

Custom Python

LLM 종속성 제거, 자동 페일오버, 동적 라우팅



RAG-KG Engine

Custom Python

KMRR 알고리즘 구현, 검색-추론 상호작용

Data

Vector DB

Milvus

대규모 벡터 데이터 검색에 특화된 최고 수준의 성능



Graph DB

Neo4j

복잡한 관계 모델링 및 논리적 추론에 최적화



RDBMS

PostgreSQL

검증된 안정성, 데이터 상태 관리의 단일 진실 공급원(SSoT)

Data Pipeline

Message Queue

Apache Kafka

대용량 실시간 이벤트 스트리밍 처리 (핫 패스)



CDC

Debezium

데이터베이스 변경 이력의 안정적인 실시간 캡처



Batch Workflow

Apache Airflow

복잡한 워크플로우의 코드 기반 정의 및 자동화 (콜드 패스)

Infrastructure

Containerization

Docker

애플리케이션의 격리된 실행 환경 보장, 배포 일관성 확보



Orchestration

Kubernetes

컨테이너 자동 배포, 스케일링, 자가 치유 및 운영 관리

🗎 상세 문서: ./01_SYSTEM_ARCHITECTURE.md

3. 핵심 컴포넌트 상세 설계 (Core Component Deep Dive)
(내용 동일)

🗎 상세 문서: ./02_CORE_COMPONENTS/

4. 데이터 모델 및 API 명세 (Data Models & API Contracts)
(내용 동일)

🗎 상세 문서: ./03_DATA_MODELS_AND_APIS/

5. 검증 및 운영 (Verification & Operations)
5.1. 검증 전략: 증명의 길 (The Proving Grounds)
본 시스템은 구축과 동시에 '증명'의 과정을 거친다. 아래의 장기 목표는 시스템의 이론적 완벽성을 현실에서 증명하기 위한 로드맵이다.

장기 검증 목표 (Long-term Verification Goals)

적대적 시뮬레이션 (Adversarial Simulation)

정량적 감사 가능성 (Quantitative Auditability)

장기적 개념 변화 대응 (Long-term Conceptual Drift)

🗎 상세 문서: ./04_PROVING_GROUNDS/TESTING_STRATEGY.md

5.2. 운영 아키텍처 (Operational Architecture)
시스템의 안정적이고 확장 가능한 운영을 위해 컨테이너 기반의 클라우드 네이티브 아키텍처를 채택한다. 모든 운영 관련 설계는 상세 문서를 따른다.

핵심 요소: 컨테이너화, 오케스트레이션, 코드형 인프라, 모니터링, 보안, 재해 복구

🗎 상세 문서: ./05_OPERATIONS/

문서 인덱스 (Document Index)
aegis-project/
│
├── AEGIS_SPECIFICATION.md              # 📜 (본 문서) 모든 설계의 입구이자 목차
│
├── 00_CHARTER.md                       # 🏛️ 프로젝트 헌장
│
├── 01_SYSTEM_ARCHITECTURE.md           # 🗺️ 통합 시스템 아키텍처
│
├── 02_CORE_COMPONENTS/                 # ⚙️ 핵심 컴포넌트 상세 설계
│   ├── 01_DUAL_TRACK_PIPELINE.md
│   ├── 02_INTERACTIVE_AI_CORE.md
│   ├── 03_LIVING_GATEWAY.md
│   └── 04_RULE_ENGINE.md
│
├── 03_DATA_MODELS_AND_APIS/            # 🔗 데이터 모델 및 API 명세
│   ├── DATABASE_SCHEMA.md
│   └── API_CONTRACT.md
│
├── 04_PROVING_GROUNDS/                 # ⚔️ 검증 전략: 증명의 길
│   └── TESTING_STRATEGY.md
│
└── 05_OPERATIONS/                      # 🏗️ 운영 및 인프라 아키텍처
    ├── 01_CONTAINER_AND_ORCHESTRATION.md
    ├── 02_INFRASTRUCTURE_AS_CODE.md
    ├── 03_MONITORING_AND_OBSERVABILITY.md
    ├── 04_SECURITY_POLICY.md
    └── 05_DISASTER_RECOVERY_PLAN.md
