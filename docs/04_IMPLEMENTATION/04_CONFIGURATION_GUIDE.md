# 이지스(Aegis) 설정 가이드

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-IMP-20250917-4.0 |
| 버전 | 4.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 모든 설정 파일, 환경 변수, 구성 옵션을 정의한다. **환경별 설정 분리**와 **보안 설정 관리**를 통해 안전하고 유연한 시스템 운영을 지원한다.

## 2. 환경 변수 설정

### 2.1. 필수 환경 변수
```bash
# 데이터베이스 설정
DATABASE_URL=postgresql://user:password@localhost:5432/aegis
REDIS_URL=redis://localhost:6379/0
MILVUS_HOST=localhost
MILVUS_PORT=19530
NEO4J_URI=bolt://localhost:7687

# API 키 설정
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 보안 설정
JWT_SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# 서비스 설정
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### 2.2. 선택적 환경 변수
```bash
# 모니터링 설정
PROMETHEUS_ENABLED=true
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# 외부 서비스 설정
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMS_API_KEY=your-sms-api-key
```

---

**📋 관련 문서**
- [보안 정책](../05_OPERATIONS/04_SECURITY_POLICY.md)
- [구현 가이드](./02_IMPLEMENTATION_GUIDE.md)