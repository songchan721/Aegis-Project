# 이지스(Aegis) 프로젝트 문서 구조 및 네이밍 컨벤션

| 항목 | 내용 |
|------|------|
| 문서 ID | APS-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 문서 구조 철학 (Documentation Philosophy)

### 1.1. 핵심 원칙
- **계층적 구조**: 상위 개념에서 하위 구현으로 자연스럽게 흐름
- **모듈화**: 각 문서는 독립적이면서도 상호 참조 가능
- **추적가능성**: 모든 결정과 변경사항을 추적 가능
- **실행가능성**: 문서만으로도 시스템 구현이 가능한 수준의 상세함

### 1.2. 문서 분류 체계
```
Level 0: 프로젝트 헌법 (Constitution)
Level 1: 시스템 아키텍처 (Architecture)
Level 2: 핵심 컴포넌트 (Core Components)
Level 3: 데이터 모델 및 API (Data & APIs)
Level 4: 구현 명세 (Implementation Specs)
Level 5: 운영 및 배포 (Operations)
Level 6: 품질 보증 (Quality Assurance)
```

## 2. 폴더 구조 (Folder Structure)

```
docs/
├── 00_FOUNDATION/                    # 프로젝트 기반
│   ├── 00_CHARTER.md                # 프로젝트 헌장
│   ├── 01_PROJECT_STRUCTURE.md      # 본 문서
│   ├── 02_SPEC_STRATEGY.md          # Spec 분할 전략
│   └── 03_GLOSSARY.md               # 용어 사전
│
├── 01_ARCHITECTURE/                  # 시스템 아키텍처
│   ├── 01_SYSTEM_OVERVIEW.md        # 전체 시스템 개요
│   ├── 02_MICROSERVICES_DESIGN.md   # 마이크로서비스 설계
│   ├── 03_DATA_ARCHITECTURE.md      # 데이터 아키텍처
│   └── 04_SECURITY_ARCHITECTURE.md  # 보안 아키텍처
│
├── 02_CORE_COMPONENTS/               # 핵심 컴포넌트
│   ├── 01_DUAL_TRACK_PIPELINE.md    # 이중 트랙 파이프라인
│   ├── 02_INTERACTIVE_AI_CORE.md    # 상호작용 AI 코어
│   ├── 03_LIVING_GATEWAY.md         # 살아있는 게이트웨이
│   ├── 04_RULE_ENGINE.md            # 규칙 엔진
│   └── 05_SCORE_FRAMEWORK.md        # S.C.O.R.E. 프레임워크
│
├── 03_DATA_AND_APIS/                 # 데이터 모델 및 API
│   ├── 01_DATABASE_SCHEMA.md        # 데이터베이스 스키마
│   ├── 02_API_CONTRACT.md           # API 명세서
│   ├── 03_EVENT_SCHEMA.md           # 이벤트 스키마 (Kafka)
│   └── 04_INTEGRATION_SPECS.md      # 외부 연동 명세
│
├── 04_IMPLEMENTATION/                # 구현 명세
│   ├── 01_MASTERPLAN.md             # 마스터플랜
│   ├── 02_IMPLEMENTATION_GUIDE.md   # 구현 가이드
│   ├── 03_DEPLOYMENT_SPECS.md       # 배포 명세
│   └── 04_CONFIGURATION_GUIDE.md    # 설정 가이드
│
├── 05_OPERATIONS/                    # 운영 및 인프라
│   ├── 01_KUBERNETES_SPECS.md       # Kubernetes 명세
│   ├── 02_MONITORING_SETUP.md       # 모니터링 설정
│   ├── 03_SECURITY_OPERATIONS.md    # 보안 운영
│   ├── 04_DISASTER_RECOVERY.md      # 재해 복구
│   └── 05_MAINTENANCE_GUIDE.md      # 유지보수 가이드
│
├── 06_QUALITY_ASSURANCE/             # 품질 보증
│   ├── 01_TESTING_STRATEGY.md       # 테스트 전략
│   ├── 02_PERFORMANCE_SPECS.md      # 성능 명세
│   ├── 03_SECURITY_TESTING.md       # 보안 테스트
│   └── 04_COMPLIANCE_CHECKLIST.md   # 컴플라이언스 체크리스트
│
├── 07_SPECIFICATIONS/                # 상세 Spec 문서들
│   ├── USER_SERVICE/                # 사용자 서비스 Spec
│   ├── POLICY_SERVICE/              # 정책 서비스 Spec
│   ├── RECOMMENDATION_SERVICE/      # 추천 서비스 Spec
│   ├── SEARCH_SERVICE/              # 검색 서비스 Spec
│   ├── DATA_PIPELINE/               # 데이터 파이프라인 Spec
│   └── FRONTEND/                    # 프론트엔드 Spec
│
└── 99_ARCHIVE/                       # 아카이브
    ├── DEPRECATED/                  # 폐기된 문서
    └── LEGACY/                      # 레거시 문서
```

## 3. 네이밍 컨벤션 (Naming Convention)

### 3.1. 파일명 규칙
```
{순서번호}_{카테고리}_{주제}.md

예시:
- 01_SYSTEM_OVERVIEW.md
- 02_MICROSERVICES_DESIGN.md
- 03_USER_SERVICE_SPEC.md
```

### 3.2. 문서 ID 규칙
```
{프로젝트코드}-{카테고리}-{날짜}-{버전}

예시:
- AEG-ARC-20250917-1.0  (Aegis Architecture)
- AEG-API-20250917-2.1  (Aegis API)
- AEG-OPS-20250917-1.0  (Aegis Operations)
```

### 3.3. 카테고리 코드
| 코드 | 의미 | 설명 |
|------|------|------|
| **FND** | Foundation | 프로젝트 기반 문서 |
| **ARC** | Architecture | 아키텍처 문서 |
| **CMP** | Component | 컴포넌트 문서 |
| **API** | API/Data | API 및 데이터 문서 |
| **IMP** | Implementation | 구현 문서 |
| **OPS** | Operations | 운영 문서 |
| **QUA** | Quality | 품질 보증 문서 |
| **SPC** | Specification | 상세 Spec 문서 |

## 4. 문서 템플릿 (Document Template)

### 4.1. 표준 헤더
```markdown
# {문서 제목}

| 항목 | 내용 |
|------|------|
| 문서 ID | {문서 ID} |
| 버전 | {버전} |
| 최종 수정일 | {날짜} |
| 작성자 | {작성자} |
| 검토자 | {검토자} |
| 승인자 | {승인자} |
| 상태 | 작성중/검토중/확정 |
| 관련 문서 | {관련 문서 링크} |
```

### 4.2. 표준 섹션 구조
```markdown
## 1. 개요 (Overview)
- 문서의 목적과 범위

## 2. 요구사항 (Requirements)
- 기능적/비기능적 요구사항

## 3. 설계 (Design)
- 상세 설계 내용

## 4. 구현 (Implementation)
- 구현 가이드라인

## 5. 테스트 (Testing)
- 테스트 방법 및 기준

## 6. 운영 (Operations)
- 운영 시 고려사항

## 7. 참고자료 (References)
- 관련 문서 및 외부 자료
```

## 5. 문서 상태 관리 (Document State Management)

### 5.1. 문서 상태
| 상태 | 설명 | 다음 단계 |
|------|------|-----------|
| **초안 (Draft)** | 작성 중인 문서 | 검토 요청 |
| **검토중 (Review)** | 검토 진행 중 | 승인/수정 요청 |
| **수정중 (Revision)** | 검토 의견 반영 중 | 재검토 요청 |
| **확정 (Approved)** | 승인된 문서 | 구현/배포 |
| **폐기 (Deprecated)** | 더 이상 사용하지 않음 | 아카이브 |

### 5.2. 버전 관리 규칙
```
Major.Minor.Patch

Major: 구조적 변경 (1.0 → 2.0)
Minor: 기능 추가/수정 (1.0 → 1.1)
Patch: 오타/형식 수정 (1.0.0 → 1.0.1)
```

## 6. 문서 간 연관관계 (Document Relationships)

### 6.1. 참조 관계
```markdown
📋 **상위 문서**: [시스템 아키텍처](../01_ARCHITECTURE/01_SYSTEM_OVERVIEW.md)
📋 **관련 문서**: [API 명세서](../03_DATA_AND_APIS/02_API_CONTRACT.md)
📋 **하위 문서**: [사용자 서비스 Spec](../07_SPECIFICATIONS/USER_SERVICE/)
```

### 6.2. 의존성 표시
```markdown
🔗 **의존성**:
- [데이터베이스 스키마](../03_DATA_AND_APIS/01_DATABASE_SCHEMA.md) (필수)
- [보안 정책](../05_OPERATIONS/03_SECURITY_OPERATIONS.md) (권장)
```

## 7. 문서 품질 기준 (Quality Standards)

### 7.1. 필수 요소
- [ ] 명확한 목적과 범위 정의
- [ ] 실행 가능한 수준의 상세함
- [ ] 관련 문서와의 일관성
- [ ] 코드 예시 및 다이어그램 포함
- [ ] 테스트 가능한 기준 제시

### 7.2. 검토 체크리스트
- [ ] 기술적 정확성
- [ ] 구현 가능성
- [ ] 문서 간 일관성
- [ ] 가독성 및 명확성
- [ ] 완전성 (누락 없음)

## 8. 도구 및 자동화 (Tools & Automation)

### 8.1. 문서 생성 도구
- **Mermaid**: 다이어그램 생성
- **PlantUML**: UML 다이어그램
- **Swagger/OpenAPI**: API 문서 자동 생성

### 8.2. 문서 검증 자동화
```yaml
# .github/workflows/docs-validation.yml
name: Documentation Validation
on: [push, pull_request]
jobs:
  validate-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Check document structure
      - name: Validate markdown syntax
      - name: Check internal links
      - name: Verify document IDs
```

---

**📋 관련 문서**
- [프로젝트 헌장](./00_CHARTER.md)
- [Spec 분할 전략](./02_SPEC_STRATEGY.md)
- [용어 사전](./03_GLOSSARY.md)