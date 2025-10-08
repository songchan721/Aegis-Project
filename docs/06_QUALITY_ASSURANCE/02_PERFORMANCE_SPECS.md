# 이지스(Aegis) 성능 명세서

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-QUA-20250917-2.0 |
| 버전 | 2.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 성능 요구사항과 측정 기준을 정의한다. 실제 운영 환경에서의 사용자 경험을 보장하기 위한 구체적이고 측정 가능한 성능 목표를 제시한다.

## 2. 성능 요구사항 개요

### 2.1. 핵심 성능 지표 (KPI)
| 지표 | 목표값 | 측정 방법 |
|------|--------|-----------|
| **응답 시간** | 95%ile < 3초 | API 응답 시간 측정 |
| **처리량** | 1,000 RPS | 동시 요청 처리 능력 |
| **가용성** | 99.9% | 월간 다운타임 < 43분 |
| **동시 사용자** | 10,000명 | 동시 접속 처리 능력 |

### 2.2. 성능 측정 환경
- **하드웨어**: AWS EC2 c5.2xlarge (8 vCPU, 16GB RAM)
- **네트워크**: 10Gbps 대역폭
- **데이터베이스**: RDS PostgreSQL (db.r5.xlarge)
- **캐시**: ElastiCache Redis (cache.r5.large)

## 3. API 성능 요구사항

### 3.1. 추천 API 성능
**엔드포인트**: `POST /api/v1/recommendations`

| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 평균 응답시간 | < 2초 | < 3초 |
| 95th percentile | < 3초 | < 5초 |
| 99th percentile | < 5초 | < 8초 |
| 처리량 | 500 RPS | 300 RPS |
| 에러율 | < 0.1% | < 1% |

**성능 테스트 시나리오**:
```javascript
// K6 성능 테스트
export let options = {
  stages: [
    { duration: '5m', target: 100 },   // 워밍업
    { duration: '10m', target: 500 },  // 목표 부하
    { duration: '5m', target: 1000 },  // 스트레스 테스트
    { duration: '5m', target: 0 },     // 쿨다운
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.001'],
  },
};
```

### 3.2. 검색 API 성능
**엔드포인트**: `GET /api/v1/policies/search`

| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 평균 응답시간 | < 500ms | < 1초 |
| 95th percentile | < 1초 | < 2초 |
| 처리량 | 2,000 RPS | 1,000 RPS |
| 캐시 히트율 | > 80% | > 60% |

### 3.3. 사용자 관리 API 성능
**엔드포인트**: `GET /api/v1/users/profile`

| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 평균 응답시간 | < 200ms | < 500ms |
| 95th percentile | < 500ms | < 1초 |
| 처리량 | 5,000 RPS | 2,000 RPS |

## 4. 데이터베이스 성능 요구사항

### 4.1. PostgreSQL 성능
| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 쿼리 응답시간 | < 100ms | < 500ms |
| 동시 연결 수 | 1,000개 | 500개 |
| CPU 사용률 | < 70% | < 85% |
| 메모리 사용률 | < 80% | < 90% |
| 디스크 I/O | < 80% | < 90% |

**주요 쿼리 성능 목표**:
```sql
-- 정책 검색 쿼리 (< 50ms)
SELECT * FROM policies 
WHERE is_active = true 
  AND target_regions && ARRAY['11'] 
  AND target_industries && ARRAY['56']
LIMIT 20;

-- 사용자 프로필 조회 (< 10ms)
SELECT profile FROM users WHERE user_id = $1;

-- 추천 이력 조회 (< 100ms)
SELECT * FROM recommendation_history 
WHERE user_id = $1 
ORDER BY created_at DESC 
LIMIT 10;
```

### 4.2. Milvus 벡터 DB 성능
| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 벡터 검색 시간 | < 50ms | < 100ms |
| 인덱스 구축 시간 | < 10분 | < 30분 |
| 메모리 사용률 | < 70% | < 85% |
| QPS | 1,000 | 500 |

**벡터 검색 성능 테스트**:
```python
import time
from pymilvus import Collection

def test_vector_search_performance():
    collection = Collection("aegis_policies_v1")
    
    # 검색 벡터 준비
    search_vectors = [[0.1] * 768]  # 768차원 벡터
    
    start_time = time.time()
    
    # 벡터 검색 실행
    results = collection.search(
        data=search_vectors,
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"ef": 32}},
        limit=10
    )
    
    search_time = (time.time() - start_time) * 1000  # ms
    
    assert search_time < 50, f"Search time {search_time}ms exceeds 50ms"
    assert len(results[0]) == 10, "Should return 10 results"
```

### 4.3. Neo4j 그래프 DB 성능
| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 그래프 쿼리 시간 | < 200ms | < 500ms |
| 동시 쿼리 수 | 100개 | 50개 |
| 메모리 사용률 | < 75% | < 90% |

**그래프 쿼리 성능 테스트**:
```cypher
// 정책 자격 요건 확인 쿼리 (< 200ms)
MATCH (p:Policy)-[:HAS_REQUIREMENT]->(r:Requirement)
WHERE p.id = $policy_id
RETURN p, collect(r) as requirements;

// 관련 정책 추천 쿼리 (< 300ms)
MATCH (p1:Policy)-[:SIMILAR_TO]-(p2:Policy)
WHERE p1.id = $policy_id
RETURN p2
ORDER BY p2.relevance_score DESC
LIMIT 5;
```

## 5. 시스템 리소스 성능 요구사항

### 5.1. CPU 사용률
| 컴포넌트 | 평상시 | 피크시 | 임계값 |
|----------|--------|--------|--------|
| API 서버 | < 50% | < 70% | < 85% |
| AI 서비스 | < 60% | < 80% | < 90% |
| 데이터베이스 | < 40% | < 70% | < 85% |
| 캐시 서버 | < 30% | < 50% | < 70% |

### 5.2. 메모리 사용률
| 컴포넌트 | 평상시 | 피크시 | 임계값 |
|----------|--------|--------|--------|
| API 서버 | < 60% | < 80% | < 90% |
| AI 서비스 | < 70% | < 85% | < 95% |
| 데이터베이스 | < 70% | < 85% | < 90% |
| 캐시 서버 | < 80% | < 90% | < 95% |

### 5.3. 네트워크 성능
| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 대역폭 사용률 | < 60% | < 80% |
| 패킷 손실률 | < 0.01% | < 0.1% |
| 네트워크 지연시간 | < 10ms | < 50ms |

## 6. 확장성 요구사항

### 6.1. 수평 확장 (Horizontal Scaling)
**목표**: 트래픽 증가 시 자동 스케일링

```yaml
# Kubernetes HPA 설정
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aegis-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aegis-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 6.2. 수직 확장 (Vertical Scaling)
**데이터베이스 스케일링 계획**:

| 사용자 수 | 인스턴스 타입 | vCPU | 메모리 | 스토리지 |
|-----------|---------------|------|--------|----------|
| < 10K | db.r5.large | 2 | 16GB | 100GB |
| 10K-50K | db.r5.xlarge | 4 | 32GB | 500GB |
| 50K-100K | db.r5.2xlarge | 8 | 64GB | 1TB |
| > 100K | db.r5.4xlarge | 16 | 128GB | 2TB |

## 7. 성능 모니터링 및 알림

### 7.1. 실시간 모니터링 메트릭
```python
from prometheus_client import Counter, Histogram, Gauge

# API 성능 메트릭
api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status']
)

api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

# 시스템 리소스 메트릭
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('memory_usage_percent', 'Memory usage percentage')
disk_usage = Gauge('disk_usage_percent', 'Disk usage percentage')

# 데이터베이스 성능 메트릭
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type']
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)
```

### 7.2. 성능 알림 규칙
```yaml
# Prometheus 알림 규칙
groups:
- name: performance_alerts
  rules:
  - alert: HighAPILatency
    expr: histogram_quantile(0.95, api_request_duration_seconds) > 3
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API latency is high"
      description: "95th percentile latency is {{ $value }}s"

  - alert: HighCPUUsage
    expr: cpu_usage_percent > 85
    for: 10m
    labels:
      severity: critical
    annotations:
      summary: "High CPU usage detected"
      description: "CPU usage is {{ $value }}%"

  - alert: DatabaseSlowQuery
    expr: histogram_quantile(0.95, db_query_duration_seconds) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Database queries are slow"
      description: "95th percentile query time is {{ $value }}s"
```

## 8. 성능 최적화 전략

### 8.1. 캐싱 전략
**다층 캐싱 구조**:
```python
class PerformanceOptimizedService:
    def __init__(self):
        self.l1_cache = {}  # 애플리케이션 메모리 캐시
        self.l2_cache = redis.Redis()  # Redis 캐시
        self.l3_cache = None  # CDN 캐시
    
    async def get_policy_with_cache(self, policy_id: str):
        # L1 캐시 확인
        if policy_id in self.l1_cache:
            return self.l1_cache[policy_id]
        
        # L2 캐시 확인
        cached_data = await self.l2_cache.get(f"policy:{policy_id}")
        if cached_data:
            policy = json.loads(cached_data)
            self.l1_cache[policy_id] = policy  # L1에 저장
            return policy
        
        # 데이터베이스에서 조회
        policy = await self.db.get_policy(policy_id)
        
        # 캐시에 저장
        await self.l2_cache.setex(
            f"policy:{policy_id}", 
            3600, 
            json.dumps(policy)
        )
        self.l1_cache[policy_id] = policy
        
        return policy
```

### 8.2. 데이터베이스 최적화
**인덱스 최적화**:
```sql
-- 복합 인덱스로 쿼리 성능 향상
CREATE INDEX CONCURRENTLY idx_policies_search 
ON policies (is_active, target_regions, target_industries) 
WHERE is_active = true;

-- 부분 인덱스로 인덱스 크기 최적화
CREATE INDEX CONCURRENTLY idx_policies_recent 
ON policies (created_at) 
WHERE created_at > NOW() - INTERVAL '1 year';

-- 함수 기반 인덱스
CREATE INDEX CONCURRENTLY idx_policies_text_search 
ON policies USING GIN (to_tsvector('korean', title || ' ' || content));
```

### 8.3. 비동기 처리 최적화
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncOptimizedService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def get_recommendations_optimized(self, query: str, user_profile: dict):
        # 병렬로 여러 작업 실행
        tasks = [
            self.vector_search(query),
            self.knowledge_graph_query(user_profile),
            self.business_rules_evaluation(user_profile)
        ]
        
        # 모든 작업이 완료될 때까지 대기
        vector_results, kg_results, rules_results = await asyncio.gather(*tasks)
        
        # 결과 통합
        return self.combine_results(vector_results, kg_results, rules_results)
    
    async def vector_search(self, query: str):
        # CPU 집약적 작업을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._cpu_intensive_vector_search, 
            query
        )
```

## 9. 성능 테스트 자동화

### 9.1. 지속적 성능 테스트
```yaml
# GitHub Actions 성능 테스트
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 매일 새벽 2시
  push:
    branches: [ main ]

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup test environment
        run: |
          docker-compose -f docker-compose.perf.yml up -d
          sleep 60  # 서비스 시작 대기
      
      - name: Run load tests
        run: |
          docker run --rm -v $PWD:/app grafana/k6 run /app/tests/performance/load-test.js
      
      - name: Run stress tests
        run: |
          docker run --rm -v $PWD:/app grafana/k6 run /app/tests/performance/stress-test.js
      
      - name: Generate performance report
        run: |
          python scripts/generate_perf_report.py
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: performance-report.html
```

### 9.2. 성능 회귀 테스트
```python
class PerformanceRegressionTest:
    def __init__(self):
        self.baseline_metrics = self.load_baseline_metrics()
    
    def test_api_performance_regression(self):
        current_metrics = self.run_performance_test()
        
        for endpoint, current_latency in current_metrics.items():
            baseline_latency = self.baseline_metrics.get(endpoint)
            
            if baseline_latency:
                # 10% 이상 성능 저하 시 실패
                regression_threshold = baseline_latency * 1.1
                
                assert current_latency <= regression_threshold, \
                    f"Performance regression detected for {endpoint}: " \
                    f"current={current_latency}ms, baseline={baseline_latency}ms"
    
    def update_baseline_if_improved(self, current_metrics):
        """성능이 개선된 경우 베이스라인 업데이트"""
        for endpoint, current_latency in current_metrics.items():
            baseline_latency = self.baseline_metrics.get(endpoint)
            
            if baseline_latency and current_latency < baseline_latency * 0.9:
                # 10% 이상 개선된 경우 베이스라인 업데이트
                self.baseline_metrics[endpoint] = current_latency
        
        self.save_baseline_metrics()
```

---

**📋 관련 문서**
- [테스트 전략](./01_TESTING_STRATEGY.md)
- [시스템 아키텍처](../01_ARCHITECTURE/01_SYSTEM_OVERVIEW.md)
- [모니터링 및 관찰가능성](../05_OPERATIONS/03_MONITORING_AND_OBSERVABILITY.md)