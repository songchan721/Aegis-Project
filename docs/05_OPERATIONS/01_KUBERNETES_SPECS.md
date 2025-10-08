# 이지스(Aegis) Kubernetes 명세서

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-OPS-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 Kubernetes 클러스터 구성, 배포 전략, 리소스 관리를 정의한다. **클라우드 네이티브** 원칙을 기반으로 한 확장 가능하고 안정적인 컨테이너 오케스트레이션을 구현한다.

## 2. 클러스터 아키텍처

### 2.1. 네임스페이스 구조
```yaml
# 환경별 네임스페이스 분리
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-production
  labels:
    environment: production
    project: aegis
---
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-staging
  labels:
    environment: staging
    project: aegis
---
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-development
  labels:
    environment: development
    project: aegis
```

### 2.2. 노드 구성
| 노드 타입 | 인스턴스 타입 | 최소 개수 | 최대 개수 | 용도 |
|-----------|---------------|-----------|-----------|------|
| **Master** | c5.large | 3 | 3 | 클러스터 관리 |
| **Worker** | c5.xlarge | 3 | 10 | 애플리케이션 실행 |
| **Data** | r5.2xlarge | 2 | 5 | 데이터베이스 워크로드 |

## 3. 서비스별 배포 명세

### 3.1. API 서비스 배포
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aegis-api
  namespace: aegis-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aegis-api
  template:
    metadata:
      labels:
        app: aegis-api
    spec:
      containers:
      - name: aegis-api
        image: aegis/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aegis-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: aegis-api-service
  namespace: aegis-production
spec:
  selector:
    app: aegis-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### 3.2. 자동 스케일링 설정
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aegis-api-hpa
  namespace: aegis-production
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

## 4. 데이터베이스 배포

### 4.1. PostgreSQL StatefulSet
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: aegis-production
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: aegis
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
      storageClassName: gp3
```

### 4.2. Redis 배포
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: aegis-production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        emptyDir: {}
```

## 5. 보안 설정

### 5.1. RBAC 설정
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: aegis-production
  name: aegis-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: aegis-rolebinding
  namespace: aegis-production
subjects:
- kind: ServiceAccount
  name: aegis-service-account
  namespace: aegis-production
roleRef:
  kind: Role
  name: aegis-role
  apiGroup: rbac.authorization.k8s.io
```

### 5.2. 네트워크 정책
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aegis-network-policy
  namespace: aegis-production
spec:
  podSelector:
    matchLabels:
      project: aegis
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: aegis-production
    - podSelector:
        matchLabels:
          app: aegis-api
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: aegis-production
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
```

## 6. 모니터링 및 로깅

### 6.1. Prometheus 설정
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: aegis-production
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'aegis-api'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - aegis-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: aegis-api
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

---

**📋 관련 문서**
- [컨테이너 및 오케스트레이션](./01_CONTAINER_AND_ORCHESTRATION.md)
- [모니터링 설정](./02_MONITORING_SETUP.md)
- [보안 운영](./03_SECURITY_OPERATIONS.md)