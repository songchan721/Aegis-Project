# User Service Implementation Plan

- [-] 1. 프로젝트 구조 및 기본 설정



  - [ ] 1.1 shared-library 설치 및 설정
    - aegis-shared 패키지 설치 (pip install aegis-shared)
    - 공통 설정 파일 작성 (로깅, 데이터베이스, 인증)
    - shared-library 초기화 코드 작성
    - _Requirements: 전체 시스템 기반, shared-library 의존성_
  
  - [ ] 1.2 프로젝트 구조 생성
    - FastAPI 프로젝트 구조 생성 (app/, tests/, requirements.txt)
    - 환경 설정 파일 및 설정 클래스 구현
    - Docker 및 docker-compose 설정 파일 작성
    - _Requirements: 전체 시스템 기반_

- [ ] 2. 데이터베이스 모델 및 스키마 구현
- [ ] 2.1 SQLAlchemy 모델 정의
  - User, LoginHistory 모델 클래스 작성
  - 데이터베이스 관계 및 인덱스 정의
  - _Requirements: 1.1, 2.1, 4.1, 5.1_

- [ ] 2.2 데이터베이스 마이그레이션 설정
  - Alembic 설정 및 초기 마이그레이션 파일 생성
  - 사용자 테이블 및 로그인 히스토리 테이블 스키마 작성
  - _Requirements: 1.1, 5.1_

- [ ] 2.3 Pydantic 모델 구현
  - 요청/응답 모델 클래스 작성 (RegisterRequest, LoginRequest, AuthResponse 등)
  - 데이터 검증 및 시리얼라이제이션 로직 구현
  - _Requirements: 1.1, 1.2, 2.1, 4.1_

- [ ] 3. 데이터 액세스 계층 구현
- [ ] 3.1 데이터베이스 연결 및 세션 관리
  - PostgreSQL 연결 설정 및 세션 팩토리 구현
  - Redis 연결 설정 및 클라이언트 구성
  - _Requirements: 2.1, 5.1, 6.1_

- [ ] 3.2 User Repository 구현
  - 사용자 CRUD 작업 메서드 구현 (create_user, find_by_email, update_user 등)
  - 로그인 히스토리 기록 메서드 구현
  - _Requirements: 1.1, 1.2, 4.1, 4.2, 5.1_

- [ ] 3.3 Session Repository 구현
  - Redis 기반 세션 관리 메서드 구현
  - 토큰 저장 및 검증 로직 구현
  - _Requirements: 2.1, 2.4, 5.2, 6.1_

- [ ] 4. 비즈니스 로직 서비스 구현
- [ ] 4.1 Authentication Service 구현
  - 사용자 등록 로직 구현 (이메일 중복 확인, 비밀번호 해시화)
  - 사용자 인증 로직 구현 (로그인, 계정 잠금 처리)
  - JWT 토큰 생성 및 검증 로직 구현
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3_

- [ ] 4.2 User Service 구현
  - 사용자 프로필 조회 및 수정 로직 구현
  - 이메일 변경 처리 로직 구현
  - 계정 삭제 처리 로직 구현
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 4.3 Token Service 구현
  - 액세스 토큰 및 리프레시 토큰 관리 로직 구현
  - 토큰 갱신 및 무효화 로직 구현
  - 세션 관리 및 만료 처리 로직 구현
  - _Requirements: 2.1, 2.4, 2.5, 5.2, 6.1, 6.3_

- [ ] 4.4 Email Service 구현
  - 이메일 인증 메일 발송 로직 구현
  - 비밀번호 재설정 메일 발송 로직 구현
  - 로그인 알림 메일 발송 로직 구현
  - _Requirements: 1.3, 1.4, 3.1, 3.2, 5.3_

- [ ] 5. 보안 및 검증 로직 구현
- [ ] 5.1 비밀번호 보안 구현
  - 비밀번호 강도 검증 함수 구현
  - bcrypt 기반 비밀번호 해시화 및 검증 구현
  - _Requirements: 1.2, 3.3_

- [ ] 5.2 계정 보안 기능 구현
  - 로그인 실패 횟수 추적 및 계정 잠금 로직 구현
  - 의심스러운 로그인 패턴 감지 로직 구현
  - 디바이스 정보 기록 및 알림 로직 구현
  - _Requirements: 2.3, 5.1, 5.3, 5.4_

- [ ] 5.3 토큰 보안 구현
  - JWT 토큰 서명 및 검증 로직 구현
  - 토큰 만료 처리 및 자동 갱신 로직 구현
  - 토큰 블랙리스트 관리 구현
  - _Requirements: 2.1, 2.4, 2.5, 6.2, 6.3_

- [ ] 6. API 엔드포인트 구현
- [ ] 6.1 Authentication API 구현
  - 사용자 등록 엔드포인트 구현 (/auth/register)
  - 로그인 엔드포인트 구현 (/auth/login)
  - 로그아웃 엔드포인트 구현 (/auth/logout)
  - 토큰 갱신 엔드포인트 구현 (/auth/refresh)
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.4, 2.5_

- [ ] 6.2 Profile API 구현
  - 프로필 조회 엔드포인트 구현 (/profile)
  - 프로필 수정 엔드포인트 구현 (/profile)
  - 이메일 변경 엔드포인트 구현 (/change-email)
  - 계정 삭제 엔드포인트 구현 (/delete-account)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 6.3 Session API 구현
  - 활성 세션 조회 엔드포인트 구현 (/sessions)
  - 특정 세션 종료 엔드포인트 구현 (/sessions/{session_id})
  - 모든 세션 종료 엔드포인트 구현 (/sessions/logout-all)
  - _Requirements: 5.5, 2.5_

- [ ] 6.4 Admin API 구현
  - 토큰 검증 엔드포인트 구현 (/auth/verify)
  - 사용자 정보 조회 엔드포인트 구현 (서비스 간 통신용)
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 7. 미들웨어 및 의존성 구현
- [ ] 7.1 인증 미들웨어 구현
  - JWT 토큰 검증 미들웨어 구현
  - 현재 사용자 정보 추출 의존성 구현
  - 권한 검사 데코레이터 구현
  - _Requirements: 6.1, 6.2_

- [ ] 7.2 보안 미들웨어 구현
  - CORS 설정 및 보안 헤더 미들웨어 구현
  - 레이트 리미팅 미들웨어 구현
  - 요청 로깅 미들웨어 구현
  - _Requirements: 6.5, 5.4_

- [ ] 7.3 예외 처리 구현
  - 커스텀 예외 클래스 정의
  - 글로벌 예외 핸들러 구현
  - 에러 응답 표준화 구현
  - _Requirements: 전체 에러 처리_

- [ ] 8. 이메일 인증 시스템 구현
- [ ] 8.1 이메일 인증 토큰 관리
  - 인증 토큰 생성 및 저장 로직 구현
  - 이메일 인증 처리 엔드포인트 구현 (/auth/verify-email)
  - 인증 메일 재발송 엔드포인트 구현 (/auth/resend-verification)
  - _Requirements: 1.3, 1.4_

- [ ] 8.2 비밀번호 재설정 시스템 구현
  - 비밀번호 재설정 요청 엔드포인트 구현 (/auth/forgot-password)
  - 비밀번호 재설정 처리 엔드포인트 구현 (/auth/reset-password)
  - 재설정 토큰 관리 및 만료 처리 구현
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 9. 단위 테스트 구현
- [ ] 9.1 서비스 계층 테스트
  - AuthService 단위 테스트 작성 (등록, 로그인, 토큰 관리)
  - UserService 단위 테스트 작성 (프로필 관리)
  - TokenService 단위 테스트 작성 (토큰 생성, 검증)
  - EmailService 단위 테스트 작성 (메일 발송)
  - _Requirements: 전체 비즈니스 로직_

- [ ] 9.2 Repository 계층 테스트
  - UserRepository 단위 테스트 작성
  - SessionRepository 단위 테스트 작성
  - 데이터베이스 모킹 및 테스트 데이터 설정
  - _Requirements: 데이터 액세스 로직_

- [ ] 9.3 API 계층 테스트
  - Authentication API 엔드포인트 테스트 작성
  - Profile API 엔드포인트 테스트 작성
  - Session API 엔드포인트 테스트 작성
  - 에러 케이스 및 예외 상황 테스트 작성
  - _Requirements: 전체 API 기능_

- [ ] 10. 통합 테스트 구현
- [ ] 10.1 전체 플로우 테스트
  - 사용자 등록부터 로그인까지 전체 플로우 테스트 작성
  - 비밀번호 재설정 플로우 테스트 작성
  - 토큰 갱신 및 세션 관리 플로우 테스트 작성
  - _Requirements: 전체 사용자 여정_

- [ ] 10.2 보안 테스트
  - 인증 우회 시도 테스트 작성
  - 토큰 조작 및 위조 시도 테스트 작성
  - 레이트 리미팅 및 계정 잠금 테스트 작성
  - _Requirements: 보안 요구사항_

- [ ] 11. 성능 최적화 및 모니터링
- [ ] 11.1 데이터베이스 최적화
  - 쿼리 성능 최적화 및 인덱스 튜닝
  - 연결 풀 설정 및 최적화
  - Redis 캐싱 전략 구현
  - _Requirements: 성능 요구사항_

- [ ] 11.2 로깅 및 모니터링 구현
  - 구조화된 로깅 시스템 구현
  - 메트릭 수집 및 모니터링 설정
  - 헬스체크 엔드포인트 구현
  - _Requirements: 운영 요구사항_

- [ ] 12. 배포 준비 및 설정
- [ ] 12.1 컨테이너화 및 배포 설정
  - Dockerfile 최적화 및 멀티스테이지 빌드 구현
  - Kubernetes 배포 매니페스트 작성
  - 환경별 설정 파일 분리 및 관리
  - _Requirements: 배포 요구사항_

- [ ] 12.2 보안 설정 및 시크릿 관리
  - 환경 변수 및 시크릿 관리 설정
  - SSL/TLS 인증서 설정
  - 보안 스캔 및 취약점 검사 설정
  - _Requirements: 보안 요구사항_