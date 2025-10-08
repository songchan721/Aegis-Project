# 이지스(Aegis) 배포 명세서

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-IMP-20250917-3.0 |
| 버전 | 3.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 배포 전략, 환경 구성, CI/CD 파이프라인을 정의한다. **무중단 배포**와 **자동화된 롤백**을 통해 안정적인 서비스 운영을 보장한다.

## 2. 배포 환경 구성

### 2.1. 환경별 구성
| 환경 | 목적 | 인프라 규모 | 데이터 |
|------|------|-------------|--------|
| **Development** | 개발 및 단위 테스트 | 최소 구성 | Mock 데이터 |
| **Staging** | 통합 테스트 및 QA | 운영 환경의 50% | 실제 데이터 샘플 |
| **Production** | 실제 서비스 운영 | 완전 구성 | 실제 데이터 |

### 2.2. Kubernetes 클러스터 구성
```yaml
# 환경별 네임스페이스
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-production
---
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-staging
---
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-development
```

## 3. CI/CD 파이프라인

### 3.1. GitHub Actions 워크플로우
```yaml
name: Aegis CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest tests/ -v --cov=app
      
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build -t aegis:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker push aegis:${{ github.sha }}
  
  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/aegis-api aegis-api=aegis:${{ github.sha }} -n aegis-staging
  
  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/aegis-api aegis-api=aegis:${{ github.sha }} -n aegis-production
```

---

**📋 관련 문서**
- [컨테이너 및 오케스트레이션](../05_OPERATIONS/01_CONTAINER_AND_ORCHESTRATION.md)
- [인프라스트럭처 코드](../05_OPERATIONS/02_INFRASTRUCTURE_AS_CODE.md)