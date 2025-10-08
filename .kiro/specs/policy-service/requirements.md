# Policy Service Requirements Document

## Introduction

정책 서비스는 이지스(Aegis) 시스템의 핵심 데이터 관리 서비스로, 정부 정책자금 정보의 **저장, 관리, 제공**을 담당합니다.

**⚠️ 역할 명확화 (중요):**
- **Policy Service**: Data Pipeline으로부터 검증된 정책 데이터를 수신하여 저장, 관리, 제공
- **Data Pipeline Service**: 외부 API 호출, 웹 크롤링, 데이터 수집 및 검증 담당

Policy Service는 Data Pipeline이 발행하는 이벤트를 구독하여 검증된 데이터를 수신하고, 이를 저장 및 관리합니다.

**개발 우선순위**: Phase 1 - 최우선 (모든 추천 및 검색 서비스의 데이터 기반)

**의존성:**
- shared-library (Phase 0) - 공통 라이브러리
- infrastructure-setup (Phase 0) - PostgreSQL, Elasticsearch, Kafka, Redis
- development-environment (Phase 0) - 개발 환경
- data-pipeline (Phase 3) - 정책 데이터 수집 및 검증

## Requirements

### Requirement 1: 정책 데이터 CRUD 관리

**User Story:** 시스템 관리자로서 정책자금 정보를 생성, 조회, 수정, 삭제할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 새로운 정책 데이터를 생성하면 THEN 시스템은 필수 필드를 검증하고 고유 ID를 부여하여 저장해야 합니다
2. WHEN 정책 ID로 조회하면 THEN 시스템은 해당 정책의 모든 상세 정보를 반환해야 합니다
3. WHEN 정책 정보를 수정하면 THEN 시스템은 변경 이력을 기록하고 버전을 관리해야 합니다
4. WHEN 정책을 삭제하면 THEN 시스템은 소프트 삭제를 수행하고 관련 서비스에 이벤트를 발행해야 합니다
5. WHEN 대량의 정책 데이터를 처리하면 THEN 시스템은 배치 처리를 통해 성능을 최적화해야 합니다

### Requirement 2: 정책 분류 및 메타데이터 관리

**User Story:** 시스템으로서 정책을 체계적으로 분류하고 검색 가능한 메타데이터를 관리할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 정책이 등록되면 THEN 시스템은 자동으로 업종, 지역, 지원형태 등의 카테고리를 분류해야 합니다
2. WHEN 정책 내용을 분석하면 THEN 시스템은 지원대상, 지원조건, 지원금액 등의 구조화된 메타데이터를 추출해야 합니다
3. WHEN 정책 태그를 관리하면 THEN 시스템은 계층적 태그 구조를 지원하고 태그 간 관계를 유지해야 합니다
4. WHEN 정책 유효성을 확인하면 THEN 시스템은 신청기간, 예산소진 여부 등을 실시간으로 업데이트해야 합니다
5. WHEN 유사한 정책을 검색하면 THEN 시스템은 메타데이터 기반으로 관련 정책들을 그룹화해야 합니다

### Requirement 3: Data Pipeline 이벤트 구독 및 처리

**User Story:** 시스템으로서 Data Pipeline Service로부터 검증된 정책 데이터를 수신하고 처리할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN Data Pipeline이 'policy.validated' 이벤트를 발행하면 THEN 시스템은 이벤트를 구독하고 정책 데이터를 수신해야 합니다
2. WHEN 검증된 정책 데이터를 수신하면 THEN 시스템은 중복 검사를 수행하고 신규 정책은 생성, 기존 정책은 업데이트해야 합니다
3. WHEN 정책 데이터 처리 중 에러가 발생하면 THEN 시스템은 에러를 로깅하고 재시도 로직을 수행해야 합니다
4. WHEN Data Pipeline이 'policy.quality_updated' 이벤트를 발행하면 THEN 시스템은 해당 정책의 품질 점수를 업데이트해야 합니다
5. WHEN Data Pipeline이 'data.consistency_check' 이벤트를 발행하면 THEN 시스템은 데이터 불일치를 해결하고 수정해야 합니다

### Requirement 4: 정책 데이터 중복 관리

**User Story:** 시스템으로서 중복된 정책 데이터를 식별하고 관리할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 새로운 정책 데이터를 수신하면 THEN 시스템은 제목과 발행기관을 기준으로 중복을 검사해야 합니다
2. WHEN 중복 정책이 발견되면 THEN 시스템은 기존 정책을 업데이트하고 새로운 버전을 생성해야 합니다
3. WHEN 중복 검사 알고리즘을 실행하면 THEN 시스템은 유사도 점수를 계산하여 중복 여부를 판단해야 합니다
4. WHEN 중복 정책 처리 중 에러가 발생하면 THEN 시스템은 에러를 로깅하고 관리자에게 알림을 보내야 합니다
5. WHEN 중복 정책 통계를 조회하면 THEN 시스템은 중복 발견 횟수와 처리 결과를 제공해야 합니다

### Requirement 5: 데이터 품질 관리 및 검증

**User Story:** 시스템으로서 수집된 정책 데이터의 품질을 검증하고 일관성을 유지할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 정책 데이터가 입력되면 THEN 시스템은 필수 필드 존재 여부와 데이터 형식을 검증해야 합니다
2. WHEN 중복 정책을 감지하면 THEN 시스템은 유사도 알고리즘을 사용하여 중복을 식별하고 병합 또는 제거해야 합니다
3. WHEN 데이터 이상치를 발견하면 THEN 시스템은 관리자에게 알림을 보내고 검토 대기 상태로 표시해야 합니다
4. WHEN 정책 내용이 불완전하면 THEN 시스템은 자동으로 추가 정보를 수집하거나 수동 검토를 요청해야 합니다
5. WHEN 데이터 품질 점수를 계산하면 THEN 시스템은 완성도, 정확도, 최신성을 종합하여 점수를 부여해야 합니다

### Requirement 6: 정책 검색 및 필터링 API

**User Story:** 다른 서비스로서 다양한 조건으로 정책을 검색하고 필터링할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 키워드로 검색하면 THEN 시스템은 정책 제목, 내용, 태그에서 관련 정책들을 반환해야 합니다
2. WHEN 복합 조건으로 필터링하면 THEN 시스템은 지역, 업종, 지원형태, 금액 범위 등의 조건을 조합하여 검색해야 합니다
3. WHEN 페이징 요청을 하면 THEN 시스템은 지정된 페이지 크기와 정렬 조건에 따라 결과를 반환해야 합니다
4. WHEN 검색 결과가 많으면 THEN 시스템은 관련도 순으로 정렬하고 하이라이팅을 제공해야 합니다
5. WHEN 검색 성능이 중요하면 THEN 시스템은 인덱싱과 캐싱을 통해 3초 이내 응답을 보장해야 합니다

### Requirement 7: 이벤트 기반 데이터 동기화

**User Story:** 시스템으로서 정책 데이터 변경 시 다른 서비스들에게 실시간으로 알림을 보낼 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 정책이 생성되면 THEN 시스템은 'policy.created' 이벤트를 Kafka로 발행해야 합니다
2. WHEN 정책이 수정되면 THEN 시스템은 'policy.updated' 이벤트와 함께 변경된 필드 정보를 포함해야 합니다
3. WHEN 정책이 삭제되면 THEN 시스템은 'policy.deleted' 이벤트를 발행하고 관련 서비스의 캐시 무효화를 트리거해야 합니다
4. WHEN 대량 업데이트가 발생하면 THEN 시스템은 배치 이벤트로 묶어서 발행하여 네트워크 부하를 최소화해야 합니다
5. WHEN 이벤트 발행이 실패하면 THEN 시스템은 재시도 로직을 수행하고 Dead Letter Queue로 전송해야 합니다

### Requirement 8: 정책 버전 관리 및 이력 추적

**User Story:** 시스템 관리자로서 정책 데이터의 변경 이력을 추적하고 이전 버전으로 롤백할 수 있어야 합니다.

#### Acceptance Criteria

1. WHEN 정책이 수정되면 THEN 시스템은 이전 버전을 보존하고 새로운 버전 번호를 부여해야 합니다
2. WHEN 변경 이력을 조회하면 THEN 시스템은 누가, 언제, 무엇을 변경했는지 상세 정보를 제공해야 합니다
3. WHEN 특정 버전으로 롤백하면 THEN 시스템은 해당 버전의 데이터를 현재 버전으로 복원해야 합니다
4. WHEN 버전 간 차이를 비교하면 THEN 시스템은 변경된 필드와 내용을 시각적으로 표시해야 합니다
5. WHEN 오래된 버전을 정리하면 THEN 시스템은 설정된 보존 정책에 따라 자동으로 아카이브해야 합니다