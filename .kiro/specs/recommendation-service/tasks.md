# Recommendation Service Implementation Plan

## Phase 1: 프로젝트 기반 설정

- [ ] 1. 프로젝트 구조 및 기본 설정
  - shared-library 설치 및 초기화 (BaseRepository, 로깅, 캐싱, 모니터링)
  - FastAPI 프로젝트 구조 생성 (app/, tests/, requirements.txt)
  - 환경 설정 클래스 구현 (Settings with Pydantic)
  - Docker 및 docker-compose 설정
  - _Requirements: shared-library 의존성_

- [ ] 2. 데이터베이스 연결 설정
  - PostgreSQL 연결 풀 설정 (pool_size=20, max_overflow=10)
  - Redis 클라이언트 설정 (pool_size=50)
  - Milvus 벡터 DB 클라이언트 구현
  - Neo4j 그래프 DB 클라이언트 구현
  - _Requirements: 2.1, 2.2, 5.1_

- [ ] 3. 데이터 모델 구현
  - [ ] 3.1 Pydantic API 모델 정의
    - RecommendationRequest, RecommendationResponse
    - PolicyRecommendation, ScoreBreakdown
    - RecommendationExplanation, SCOREExplanation
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 3.2 SQLAlchemy DB 모델 구현
    - recommendation_sessions 테이블 모델
    - user_feedbacks 테이블 모델
    - recommendation_history 테이블 모델
    - user_preferences 테이블 모델
    - _Requirements: 6.1, 6.2, 8.1_
  
  - [ ] 3.3 Milvus 컬렉션 스키마 정의
    - policy_embeddings 컬렉션 (768차원 벡터)
    - 인덱스 설정 (IVF_FLAT, COSINE)
    - _Requirements: 2.1_
  
  - [ ] 3.4 Neo4j 그래프 스키마 정의
    - Policy, Requirement 노드 레이블
    - HAS_REQUIREMENT, RELATED_TO 관계
    - 인덱스 및 제약조건
    - _Requirements: 2.2, 2.3_

## Phase 2: Query Processing Layer

- [ ] 4. Query Parser 구현
  - 자연어 쿼리 파싱 로직 (ParsedQuery 데이터 클래스)
  - 구조화된 쿼리 변환 시스템
  - 쿼리 검증 및 정규화
  - _Requirements: 1.1, 1.2_

- [ ] 5. Intent Analyzer 구현
  - 패턴 기반 의도 분류 (IntentType enum)
  - LLM 기반 의도 분류 (폴백)
  - 의도 신뢰도 계산
  - _Requirements: 1.1, 1.4_

- [ ] 6. Entity Extractor 구현
  - 정규식 기반 엔티티 추출 (지역, 업종, 금액)
  - LLM 기반 엔티티 추출 (보완)
  - 엔티티 검증 및 정규화
  - _Requirements: 1.2, 4.1_

- [ ] 7. Context Builder 구현
  - 사용자 프로필과 쿼리 통합
  - 검색 컨텍스트 생성
  - 모호성 감지 및 명확화 질문 생성
  - _Requirements: 1.3, 4.3, 8.2_


## Phase 3: AI Core Engine

- [ ] 8. Living Gateway 구현
  - [ ] 8.1 LLM Provider 클라이언트
    - OpenAI GPT-4 클라이언트
    - Anthropic Claude 클라이언트
    - Google Gemini 클라이언트
    - Local LLM 클라이언트
    - _Requirements: 7.1_
  
  - [ ] 8.2 Provider Health Monitoring
    - LLM 서비스 상태 모니터링
    - 응답 시간 및 품질 메트릭 수집
    - 자동 장애 감지
    - _Requirements: 7.2, 7.4_
  
  - [ ] 8.3 Fallback Chain
    - 다중 LLM 폴백 체인 (OpenAI → Claude → Gemini → Local → Rule-based)
    - 응답 품질 검증
    - 재시도 로직
    - _Requirements: 7.2, 7.3, 7.5_

- [ ] 9. RAG Engine 구현
  - [ ] 9.1 Embedding Service
    - sentence-transformers 모델 로드 (paraphrase-multilingual-mpnet-base-v2)
    - 쿼리 임베딩 생성
    - 임베딩 캐싱
    - _Requirements: 2.1_
  
  - [ ] 9.2 Vector Search
    - Milvus 벡터 검색 (COSINE 유사도)
    - 필터 조건 기반 검색
    - Top-K 후보 선별 (K=50)
    - _Requirements: 2.1, 2.5_
  
  - [ ] 9.3 Knowledge Graph Reasoner
    - Neo4j 기반 지식 그래프 추론
    - 자격 요건 매칭 로직
    - 정책 간 관계 분석 (RELATED_TO, REQUIRES, EXCLUDES)
    - _Requirements: 2.2, 2.3_
  
  - [ ] 9.4 KMRR Ranker
    - 벡터 유사도 + 지식 그래프 사실 통합
    - 비즈니스 규칙 적용
    - 최종 점수 계산 및 순위 결정
    - _Requirements: 2.4_

- [ ] 10. S.C.O.R.E. Framework 구현
  - [ ] 10.1 S.C.O.R.E. Calculator
    - Specificity (구체성) 점수 계산
    - Consistency (일관성) 점수 계산
    - Observability (관찰가능성) 데이터 생성
    - Reproducibility (재현가능성) 점수 계산
    - Explainability (설명가능성) 텍스트 생성
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 10.2 Evidence Generator
    - 추천 근거 증거 체인 생성
    - 증거 신뢰도 계산
    - _Requirements: 3.2_
  
  - [ ] 10.3 Explanation Builder
    - 사용자 친화적 설명 텍스트 생성
    - 설명 상세도 조절 (basic/standard/detailed)
    - _Requirements: 3.4, 3.5_

## Phase 4: 개인화 및 학습

- [ ] 11. Personalization Engine 구현
  - 사용자 프로필 기반 개인화
  - 과거 관심 정책 분석
  - 개인화 가중치 동적 조정
  - _Requirements: 4.1, 4.2, 4.5_

- [ ] 12. Feedback Processor 구현
  - 명시적 피드백 수집 (별점, 유용성)
  - 암시적 피드백 분석 (클릭, 신청, 무시)
  - 피드백 기반 알고리즘 튜닝
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 13. A/B Tester 구현
  - 추천 알고리즘 A/B 테스트 프레임워크
  - 실험 설계 및 결과 분석
  - 통계적 유의성 검증
  - _Requirements: 6.5, 10.5_

- [ ] 14. Performance Optimizer 구현
  - 추천 성능 자동 최적화
  - 알고리즘 파라미터 자동 튜닝
  - 성능 지표 기반 적응적 조정
  - _Requirements: 10.3, 10.4_

## Phase 5: 세션 및 캐싱

- [ ] 15. Session Manager 구현
  - 추천 세션 생성 및 관리
  - 세션 상태 추적 (Redis)
  - 세션 만료 및 정리 (TTL=1800초)
  - _Requirements: 8.1, 8.5_

- [ ] 16. Context Store 구현
  - 대화 컨텍스트 저장 및 조회
  - 컨텍스트 압축 및 요약
  - _Requirements: 8.2, 8.4_

- [ ] 17. Cache Manager 구현
  - Redis 기반 다층 캐싱 (추천 결과, 사용자 프로필, 정책 메타데이터)
  - 캐시 키 생성 및 무효화 전략
  - 캐시 히트율 최적화
  - _Requirements: 5.1, 5.2, 5.3_

## Phase 6: API 및 통합

- [ ] 18. API 엔드포인트 구현
  - [ ] 18.1 Recommendation API
    - POST /api/v1/recommendations (추천 생성)
    - GET /api/v1/recommendations/{id} (추천 조회)
    - _Requirements: 1.1, 2.1, 3.1_
  
  - [ ] 18.2 Feedback API
    - POST /api/v1/feedback (피드백 수집)
    - GET /api/v1/feedback/stats (피드백 통계)
    - _Requirements: 6.1, 6.2_
  
  - [ ] 18.3 Session API
    - POST /api/v1/sessions (세션 생성)
    - GET /api/v1/sessions/{id} (세션 조회)
    - PUT /api/v1/sessions/{id}/context (컨텍스트 업데이트)
    - _Requirements: 8.1, 8.2_
  
  - [ ] 18.4 Health Check API
    - GET /health (Liveness Probe)
    - GET /health/ready (Readiness Probe)

- [ ] 19. 외부 서비스 클라이언트 구현
  - [ ] 19.1 Policy Service Client
    - Circuit Breaker 적용 (failure_threshold=5, recovery_timeout=60)
    - 정책 데이터 조회 API
    - _Requirements: 2.2_
  
  - [ ] 19.2 User Service Client
    - Circuit Breaker 적용
    - 사용자 프로필 조회 API
    - _Requirements: 4.1_
  
  - [ ] 19.3 Search Service Client
    - Circuit Breaker 적용
    - 키워드 검색 API (폴백용)
    - _Requirements: 1.5_

- [ ] 20. 이벤트 구독 구현
  - [ ] 20.1 Policy Event Handler
    - policy.created 이벤트 처리 (임베딩 생성)
    - policy.updated 이벤트 처리 (임베딩 업데이트, 캐시 무효화)
    - policy.deleted 이벤트 처리 (임베딩 삭제)
    - _Requirements: 5.3_
  
  - [ ] 20.2 User Event Handler
    - user.profile_updated 이벤트 처리 (캐시 무효화)
    - _Requirements: 4.5_


## Phase 7: Production 준비 ⭐

- [ ] 21. Error Handling 구현
  - 중앙 에러 코드 레지스트리 사용 (ErrorCode from aegis_shared)
  - ServiceException 기반 에러 처리
  - 에러 복구 전략 (LLM 폴백, 규칙 기반 폴백)
  - _Requirements: 1.5, 7.3_

- [ ] 22. Monitoring 구현
  - [ ] 22.1 Prometheus 메트릭
    - recommendation_requests_total (Counter)
    - recommendation_latency_seconds (Histogram)
    - llm_requests_total (Counter)
    - llm_fallback_count (Counter)
    - vector_search_latency_seconds (Histogram)
    - cache_hit_rate (Gauge)
    - _Requirements: 10.1_
  
  - [ ] 22.2 Grafana 대시보드
    - Request Rate 패널
    - Response Time (p50, p95, p99) 패널
    - Error Rate 패널
    - LLM Provider Status 패널
    - Cache Hit Rate 패널
    - _Requirements: 10.1_
  
  - [ ] 22.3 알림 규칙
    - HighErrorRate (> 5% for 5m)
    - SlowResponseTime (p95 > 3s for 5m)
    - LLMServiceDown (no success for 2m)
    - LowCacheHitRate (< 50% for 10m)
    - _Requirements: 10.2_

- [ ] 23. Logging 구현
  - 구조화된 로깅 (aegis_shared.logging)
  - 자동 컨텍스트 추가 (request_id, user_id)
  - 로그 레벨 설정 (DEBUG/INFO/WARNING/ERROR)
  - Elasticsearch 연동

- [ ] 24. Configuration Management
  - Pydantic Settings 클래스 구현
  - 환경별 설정 분리 (dev/staging/prod)
  - Secret 관리 (Kubernetes Secrets)
  - ConfigMap 설정

- [ ] 25. Kubernetes 배포 준비
  - [ ] 25.1 Deployment 매니페스트
    - 리소스 요청/제한 (CPU: 1-2 cores, Memory: 2-4GB)
    - Liveness/Readiness Probe 설정
    - 환경 변수 및 Secret 마운트
    - _Requirements: 확장성_
  
  - [ ] 25.2 HPA 설정
    - minReplicas: 3, maxReplicas: 20
    - CPU 70%, Memory 80% 기준 스케일링
    - 초당 100 요청 기준 추가 스케일링
    - _Requirements: 확장성_
  
  - [ ] 25.3 Service 매니페스트
    - ClusterIP 타입
    - HTTP (8000), Metrics (9090) 포트
  
  - [ ] 25.4 ConfigMap 및 Secret
    - 데이터베이스 연결 정보
    - LLM API 키
    - 서비스 설정

## Phase 8: 테스트

- [ ] 26. 단위 테스트
  - [ ] 26.1 Query Processing 테스트
    - QueryParser 테스트
    - IntentAnalyzer 테스트
    - EntityExtractor 테스트
    - _Requirements: 1.1, 1.2_
  
  - [ ] 26.2 AI Core Engine 테스트
    - LivingGateway 폴백 체인 테스트
    - RAG Engine 테스트
    - KMRR Ranker 테스트
    - _Requirements: 2.1, 2.4, 7.2_
  
  - [ ] 26.3 S.C.O.R.E. Framework 테스트
    - SCORECalculator 테스트
    - EvidenceGenerator 테스트
    - ExplanationBuilder 테스트
    - _Requirements: 3.1, 3.2_

- [ ] 27. 통합 테스트
  - [ ] 27.1 End-to-End 추천 플로우 테스트
    - 전체 추천 프로세스 테스트
    - 다양한 쿼리 시나리오 테스트
    - _Requirements: 전체 플로우_
  
  - [ ] 27.2 LLM Fallback 테스트
    - 다중 LLM 폴백 체인 테스트
    - 장애 상황 시뮬레이션
    - _Requirements: 7.2, 7.3_
  
  - [ ] 27.3 성능 테스트
    - 응답 시간 SLA 검증 (< 3초)
    - 동시 사용자 처리 성능 테스트
    - 캐시 히트율 검증
    - _Requirements: 2.5, 5.1_

- [ ] 28. 보안 테스트
  - API 인증 테스트 (JWT)
  - 데이터 암호화 검증
  - Rate Limiting 테스트

## Phase 9: 문서화 및 배포

- [ ] 29. API 문서화
  - OpenAPI 스펙 작성
  - Swagger UI 설정
  - API 사용 예시

- [ ] 30. 운영 문서 작성
  - 배포 가이드
  - 트러블슈팅 가이드
  - 모니터링 가이드
  - 백업 및 복구 절차

- [ ] 31. CI/CD 파이프라인
  - GitHub Actions 워크플로우
  - 자동 테스트 실행
  - Docker 이미지 빌드 및 푸시
  - Kubernetes 자동 배포

- [ ] 32. 프로덕션 배포
  - Staging 환경 배포 및 검증
  - Production 환경 배포
  - 배포 후 모니터링
  - 롤백 계획 준비

---

## 작업 우선순위

**Critical Path (필수):**
1. Phase 1-2: 기반 설정 및 Query Processing (1-7)
2. Phase 3: AI Core Engine (8-10)
3. Phase 6: API 구현 (18-20)
4. Phase 7: Production 준비 (21-25)

**High Priority (높음):**
5. Phase 4: 개인화 및 학습 (11-14)
6. Phase 5: 세션 및 캐싱 (15-17)
7. Phase 8: 테스트 (26-27)

**Medium Priority (중간):**
8. Phase 8: 보안 테스트 (28)
9. Phase 9: 문서화 (29-30)

**Low Priority (낮음):**
10. Phase 9: CI/CD 및 배포 (31-32)

---

## 예상 소요 시간

- Phase 1-2: 3-4일
- Phase 3: 5-7일
- Phase 4-5: 4-5일
- Phase 6: 3-4일
- Phase 7: 3-4일
- Phase 8: 4-5일
- Phase 9: 2-3일

**총 예상 시간: 24-32일**
