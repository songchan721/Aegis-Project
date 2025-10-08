# Shared Library Implementation Plan

- [x] 1. 프로젝트 기본 구조 설정
  - [x] Python 패키지 구조 생성 (aegis_shared/)
  - [x] pyproject.toml 설정 (Poetry 또는 setuptools)
  - [x] README.md, CHANGELOG.md, LICENSE 작성
  - [x] .gitignore, .editorconfig 설정
  - _Requirements: 전체 시스템 기반_

- [x] 2. Database 모듈 구현
  - [x] 2.1 연결 관리자 구현
    - [x] DatabaseManager 클래스 작성
    - [x] 연결 풀 설정 및 관리
    - [x] 세션 컨텍스트 매니저 구현
    - _Requirements: 1.1, 1.5_

  - [x] 2.2 Base Repository 패턴 구현
    - [x] BaseRepository 제네릭 클래스 작성
    - [x] CRUD 메서드 구현 (create, read, update, delete, list)
    - [x] 페이지네이션 및 필터링 지원
    - [x] 소프트 삭제 기능 구현
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 트랜잭션 관리 구현
    - [x] 트랜잭션 컨텍스트 매니저
    - [x] 자동 커밋/롤백 로직
    - [x] 중첩 트랜잭션 지원
    - _Requirements: 1.3_

  - [x] 2.4 에러 처리 및 재시도 로직
    - [x] 데이터베이스 예외 래핑
    - [x] 재시도 데코레이터 구현
    - [x] 연결 복구 메커니즘
    - _Requirements: 1.4_

- [x] 3. Authentication 모듈 구현
  - [x] 3.1 JWT Handler 구현
    - [x] JWT 토큰 생성 함수
    - [x] JWT 토큰 검증 함수
    - [x] 토큰 갱신 로직
    - _Requirements: 2.1_

  - [x] 3.2 인증 미들웨어 구현
    - [x] FastAPI 미들웨어 작성
    - [x] 토큰 자동 검증
    - [x] 사용자 정보 추출 및 컨텍스트 설정
    - _Requirements: 2.2_

  - [x] 3.3 권한 관리 구현
    - [x] RBAC 데코레이터 작성
    - [x] 권한 검증 로직
    - [x] 역할 기반 접근 제어
    - _Requirements: 2.3_

  - [x] 3.4 서비스 계정 토큰 관리
    - [x] 서비스 간 통신용 토큰 생성
    - [x] 서비스 계정 검증
    - _Requirements: 2.5_

- [x] 4. Logging 모듈 구현
  - [x] 4.1 구조화된 로거 설정
    - [x] structlog 설정 및 초기화
    - [x] JSON 포맷터 구현
    - [x] 로그 레벨 관리
    - [x] _Requirements: 3.1, 3.3_

  - [x] 4.2 로깅 컨텍스트 관리
    - [x] ContextVar를 사용한 컨텍스트 변수
    - [x] request_id, user_id, service_name 자동 추가
    - [x] 컨텍스트 프로세서 구현
    - [x] _Requirements: 3.2_

  - [x] 4.3 에러 로깅 강화
    - [x] 스택 트레이스 자동 포함
    - [x] 컨텍스트 정보 자동 추가
    - [x] 에러 추적 시스템 연동 (Sentry)
    - [x] _Requirements: 3.4_

  - [x] 4.4 로그 핸들러 구현
    - [x] Elasticsearch 핸들러
    - [x] 파일 로테이션 핸들러
    - [x] 콘솔 핸들러
    - [x] _Requirements: 3.5_

- [x] 5. Messaging 모듈 구현
  - [x] 5.1 Kafka Producer 구현
    - [x] KafkaProducer 래퍼 클래스
    - [x] 연결 관리 및 재시도 로직
    - [x] 메시지 직렬화
    - _Requirements: 4.1_

  - [x] 5.2 Event Publisher 구현
    - [x] 이벤트 발행 인터페이스
    - [x] 메타데이터 자동 추가
    - [x] 배치 발행 지원
    - _Requirements: 4.1, 4.5_

  - [x] 5.3 Event Subscriber 구현
    - [x] Kafka Consumer 래퍼
    - [x] 이벤트 핸들러 등록 데코레이터
    - [x] 자동 역직렬화
    - _Requirements: 4.4_

  - [x] 5.4 이벤트 스키마 정의
    - [x] Pydantic 기반 이벤트 모델
    - [x] 스키마 검증
    - [x] 버전 관리
    - _Requirements: 4.2_

  - [x] 5.5 에러 처리 및 DLQ
    - [x] 재시도 로직 구현
    - [x] Dead Letter Queue 전송
    - [x] 에러 로깅
    - _Requirements: 4.3_

- [x] 6. Monitoring 모듈 구현
  - [x] 6.1 Prometheus 메트릭 수집
    - [x] 메트릭 수집 데코레이터
    - [x] API 요청 메트릭 (응답 시간, 상태 코드)
    - [x] 데이터베이스 쿼리 메트릭
    - _Requirements: 6.1, 6.2_

  - [x] 6.2 커스텀 메트릭 지원
    - [x] Counter, Gauge, Histogram 래퍼
    - [x] 메트릭 등록 및 관리
    - [x] _Requirements: 6.3_

  - [x] 6.3 메트릭 엔드포인트 구현
    - [x] /metrics 엔드포인트 생성
    - [x] Prometheus 형식 출력
    - [x] _Requirements: 6.4_

  - [x] 6.4 분산 추적 구현
    - [x] OpenTelemetry 통합
    - [x] trace_id 전파
    - [x] 스팬 생성 및 관리
    - [x] _Requirements: 6.5_

  - [x] 6.5 헬스 체크 구현
    - [x] /health 엔드포인트
    - [x] 의존성 서비스 상태 확인
    - [x] 상태 집계 로직
    - [x] _Requirements: 6.1_

- [x] 7. Error Handling 모듈 구현
  - [x] 7.1 공통 예외 클래스 정의
    - [x] AegisBaseException 기본 클래스
    - [x] 도메인별 예외 클래스 (Auth, Database, Validation 등)
    - [x] 에러 코드 정의
    - _Requirements: 5.1, 5.2_

  - [x] 7.2 예외 핸들러 구현
    - [x] FastAPI 예외 핸들러
    - [x] 표준화된 에러 응답 형식
    - [x] HTTP 상태 코드 매핑
    - _Requirements: 5.3_

  - [x] 7.3 검증 에러 처리
    - [x] Pydantic 검증 에러 변환
    - [x] 필드별 에러 메시지
    - [x] _Requirements: 5.4_

  - [x] 7.4 에러 추적 시스템 연동
    - [x] Sentry 통합
    - [x] 자동 에러 리포팅
    - [x] _Requirements: 5.5_

- [x] 8. Models 모듈 구현
  - [x] 8.1 Base Model 정의
    - [x] BaseEntity Pydantic 모델
    - [x] 공통 필드 (id, created_at, updated_at, deleted_at)
    - [x] JSON 직렬화 설정
    - _Requirements: 7.1, 7.2_

  - [x] 8.2 데이터 계약 정의
    - [x] 서비스 간 공유 모델
    - [x] 버전 관리 전략
    - _Requirements: 7.1_

  - [x] 8.3 공통 Enum 정의
    - [x] 상태 코드, 역할, 권한 등
    - _Requirements: 7.1_

  - [x] 8.4 페이지네이션 모델
    - [x] PaginatedResponse 모델
    - [x] 페이지네이션 헬퍼 함수
    - _Requirements: 7.1, 10.5_

  - [x] 8.5 직렬화 유틸리티
    - [x] JSON, dict, ORM 모델 간 변환
    - [x] 날짜/시간 처리
    - [x] 민감 데이터 마스킹
    - _Requirements: 7.3, 7.5_

- [x] 9. Cache 모듈 구현
  - [x] 9.1 Redis 클라이언트 래퍼
    - [x] Redis 연결 관리
    - [x] 기본 캐시 작업 (get, set, delete)
    - [x] TTL 관리
    - _Requirements: 8.1, 8.3_

  - [x] 9.2 캐싱 데코레이터 구현
    - [x] 함수 결과 자동 캐싱
    - [x] 캐시 키 자동 생성
    - [x] TTL 설정
    - _Requirements: 8.1, 8.2_

  - [x] 9.3 캐시 무효화 전략
    - [x] 수동 무효화 함수
    - [x] 패턴 기반 무효화
    - _Requirements: 8.4_

  - [x] 9.4 캐시 메트릭 수집
    - [x] 히트율 측정
    - [x] 메트릭 자동 수집
    - _Requirements: 8.5_

- [x] 10. Config 모듈 구현
  - [x] 10.1 설정 관리자 구현
    - [x] 환경 변수 로드
    - [x] .env 파일 지원
    - [x] 설정 병합 로직
    - _Requirements: 9.1_

  - [x] 10.2 설정 검증
    - [x] Pydantic 기반 검증
    - [x] 필수 설정 확인
    - [x] 타입 검증
    - _Requirements: 9.2, 9.3_

  - [x] 10.3 시크릿 관리
    - [x] 환경 변수에서 시크릿 로드
    - [x] Vault 연동 (선택적)
    - [x] 시크릿 암호화
    - _Requirements: 9.4_

  - [x] 10.4 환경별 설정
    - [x] development, staging, production 구분
    - [x] 환경 자동 감지
    - _Requirements: 9.5_

- [x] 11. Utils 모듈 구현
  - [x] 11.1 날짜/시간 유틸리티
    - [x] 파싱, 포맷팅 함수
    - [x] 시간대 변환
    - [x] UTC 표준화
    - _Requirements: 10.1_

  - [x] 11.2 문자열 유틸리티
    - [x] 정규화, 검증 함수
    - [x] 슬러그 생성
    - [x] 텍스트 변환
    - _Requirements: 10.2_

  - [x] 11.3 암호화 유틸리티
    - [x] 해싱 함수 (bcrypt, argon2)
    - [x] 암호화/복호화 함수
    - [x] 토큰 생성
    - _Requirements: 10.3_

  - [x] 11.4 파일 유틸리티
    - [x] 파일 업로드/다운로드
    - [x] 파일 검증
    - [x] MIME 타입 감지
    - _Requirements: 10.4_

  - [x] 11.5 검증 유틸리티
    - [x] 이메일, 전화번호 검증
    - [x] 비밀번호 강도 검증
    - [x] 커스텀 검증 함수
    - _Requirements: 10.2_

  - [x] 11.6 페이지네이션 유틸리티
    - [x] 오프셋 계산 함수
    - [x] 페이지네이션 헬퍼
    - [x] 파라미터 검증 및 정규화
    - _Requirements: 10.5_

- [x] 12. 중앙 스키마 레지스트리 구현
  - [x] 12.1 스키마 정의 모델 작성
    - [x] SchemaColumn, SchemaReference, SchemaDefinition Pydantic 모델
    - [x] YAML 직렬화/역직렬화 지원
    - [x] 스키마 버전 관리
    - _Requirements: 11.1, 11.3_

  - [x] 12.2 SchemaRegistry 클래스 구현
    - [x] 스키마 파일 로드 및 저장
    - [x] 스키마 등록 및 조회 기능
    - [x] 의존성 그래프 생성
    - _Requirements: 11.1, 11.2_

  - [x] 12.3 의존성 분석 기능 구현
    - [x] 의존 서비스 목록 조회
    - [x] 순환 의존성 탐지
    - [x] 위상 정렬을 통한 마이그레이션 순서 생성
    - _Requirements: 11.2, 12.2_

  - [x] 12.4 스키마 검증 기능 구현
    - [x] 참조 무결성 검증
    - [x] 스키마 간 호환성 검증
    - [x] 버전 호환성 체크
    - _Requirements: 11.4, 11.5_

  - [x] 12.5 문서 자동 생성 기능
    - [x] Markdown 형식 스키마 문서 생성
    - [x] ERD 다이어그램 생성 (Mermaid)
    - [x] 의존성 그래프 시각화
    - _Requirements: 11.6_

  - [x] 12.6 스키마 레지스트리 디렉토리 구조 생성
    - [x] .kiro/schemas/ 디렉토리 생성
    - [x] registry.yaml 템플릿 파일 생성
    - [x] 샘플 스키마 파일 작성 (users.yaml, policies.yaml)
    - _Requirements: 11.1_

- [x] 13. 마이그레이션 조율 시스템 구현
  - [x] 13.1 MigrationStep 데이터 모델 작성
    - [x] 마이그레이션 단계 정의
    - [x] 상태 관리 (PENDING, RUNNING, COMPLETED, FAILED, ROLLED_BACK)
    - [x] 의존성 추적
    - _Requirements: 12.1_

  - [x] 13.2 MigrationCoordinator 클래스 구현
    - [x] 마이그레이션 계획 수립 (plan_migration)
    - [x] 영향 받는 서비스 자동 식별
    - [x] 마이그레이션 순서 결정
    - _Requirements: 12.1, 12.2_

  - [x] 13.3 마이그레이션 검증 기능 구현
    - [x] 사전 검증 (validate_migration)
    - [x] 데이터 손실 위험 감지
    - [x] 호환성 문제 경고
    - _Requirements: 12.4_

  - [x] 13.4 조율된 마이그레이션 실행
    - [x] 순차적 마이그레이션 실행
    - [x] 각 단계별 상태 추적
    - [x] 실행 로그 기록
    - _Requirements: 12.2_

  - [x] 13.5 롤백 메커니즘 구현
    - [x] 실패 시 자동 롤백
    - [x] 역순 롤백 실행
    - [x] 롤백 이력 기록
    - _Requirements: 12.3_

  - [x] 13.6 마이그레이션 이력 관리
    - [x] 이력 조회 기능
    - [x] 서비스별 필터링
    - [x] 영향 분석 보고서 생성
    - _Requirements: 12.5_

  - [x]* 13.7 마이그레이션 테스트
    - [x] 단위 테스트 작성
    - [x] 통합 테스트 (실제 DB 사용)
    - [x] 롤백 시나리오 테스트
    - _Requirements: 12.1-12.5_

- [x] 14. 테스트 작성


  - [x] 14.1 단위 테스트


    - 각 모듈별 단위 테스트 작성
    - pytest fixtures 구성
    - Mock 객체 활용
    - _Requirements: 모든 요구사항_

  - [x] 14.2 통합 테스트


    - 데이터베이스 통합 테스트
    - Kafka 통합 테스트
    - Redis 통합 테스트
    - _Requirements: 모든 요구사항_

  - [x] 14.3 테스트 커버리지


    - 커버리지 80% 이상 달성
    - 커버리지 리포트 생성
    - _Requirements: 모든 요구사항_

- [x] 15. 문서화

  - [x] 15.1 API 문서 작성


    - 각 모듈별 사용법 문서
    - 코드 예시 포함
    - docstring 작성
    - _Requirements: 모든 요구사항_

  - [x] 15.2 사용 가이드 작성


    - 빠른 시작 가이드
    - 모범 사례
    - 트러블슈팅 가이드
    - _Requirements: 모든 요구사항_



  - [x] 15.3 스키마 레지스트리 사용 가이드
    - 스키마 등록 방법
    - 마이그레이션 조율 사용법
    - 영향 분석 보고서 활용
    - _Requirements: 11.1-11.6, 12.1-12.5_

  - [x] 15.4 CHANGELOG 관리
    - 버전별 변경사항 기록
    - Breaking changes 명시
    - _Requirements: 모든 요구사항_

- [x] 16. 패키지 배포


  - [x] 16.1 빌드 설정


    - pyproject.toml 최종 설정
    - 의존성 버전 고정
    - 빌드 스크립트 작성
    - _Requirements: 전체 시스템_



  - [x] 16.2 Private PyPI 설정





    - PyPI 서버 설정 또는 Artifactory 사용
    - 패키지 업로드 스크립트

    - 버전 관리 자동화
    - _Requirements: 전체 시스템_

  - [x] 16.3 CI/CD 파이프라인
    - [x] GitHub Actions workflow 파일 작성 (shared-library-ci.yml)
    - [x] 자동 테스트 실행 (252 tests)
    - [x] 코드 품질 검사 (black, isort, flake8, mypy)
    - [x] 보안 스캔 (bandit, safety, trivy)
    - [x] 자동 빌드 및 배포 (Poetry build + Private PyPI)
    - [x] 버전 태깅 자동화 (release.yml workflow)
    - [x] CI/CD 사용 가이드 문서 작성
    - _Requirements: 전체 시스템_


- [x] 17. 통합 검증

  - [x] 17.1 샘플 서비스 작성




    - shared-library를 사용하는 샘플 서비스
    - 모든 기능 사용 예시
    - _Requirements: 모든 요구사항_

  - [x] 17.2 성능 테스트


    - 벤치마크 테스트
    - 메모리 사용량 측정
    - 병목 지점 파악
    - _Requirements: 모든 요구사항_


  - [x] 17.3 다른 서비스와 통합 테스트

    - user-service에 적용
    - policy-service에 적용
    - 통합 동작 확인
    - _Requirements: 모든 요구사항_
