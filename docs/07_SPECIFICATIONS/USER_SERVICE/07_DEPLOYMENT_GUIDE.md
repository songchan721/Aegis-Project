# 사용자 서비스 배포 가이드

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-SPC-USER-20250917-7.0 |
| 버전 | 7.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 사용자 서비스를 프로덕션 환경에 배포하기 위한 상세 가이드를 제공한다. **컨테이너 기반 배포**, **무중단 배포**, **모니터링 설정** 등 운영 환경에서 필요한 모든 요소를 다룬다.

## 2. 배포 아키텍처

### 2.1. 전체 배포 구조

```mermaid
graph TB
    subgraph "Load Balancer"
        A[ALB/NLB]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "User Service Namespace"
            B[User Service Pod 1]
            C[User Service Pod 2]
            D[User Service Pod 3]
        end
        
        subgraph "Database Namespace"
            E[PostgreSQL Primary]
            F[PostgreSQL Replica]
        end
        
        subgraph "Cache Namespace"
            G[Redis Cluster]
        end
        
        subgraph "Message Queue"
            H[Kafka Cluster]
        end
    end
    
    subgraph "External Services"
        I[Business Registry API]
        J[Email Service]
        K[SMS Service]
    end
    
    A --> B
    A --> C
    A --> D
    
    B --> E
    C --> E
    D --> E
    
    B --> G
    C --> G
    D --> G
    
    B --> H
    C --> H
    D --> H
    
    B --> I
    B --> J
    B --> K
```

### 2.2. 배포 환경 구성

#### 개발 환경 (Development)
- **인스턴스**: 1개 Pod
- **리소스**: CPU 0.5 core, Memory 1GB
- **데이터베이스**: 단일 인스턴스
- **캐시**: Redis 단일 노드

#### 스테이징 환경 (Staging)
- **인스턴스**: 2개 Pod
- **리소스**: CPU 1 core, Memory 2GB
- **데이터베이스**: Primary-Replica 구성
- **캐시**: Redis 클러스터 (3 노드)

#### 프로덕션 환경 (Production)
- **인스턴스**: 3개 Pod (최소), Auto Scaling
- **리소스**: CPU 2 core, Memory 4GB
- **데이터베이스**: Primary-Replica 구성 + 백업
- **캐시**: Redis 클러스터 (6 노드)

## 3. 컨테이너화

### 3.1. Dockerfile

```dockerfile
# Multi-stage build for Python application
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Set work directory
WORKDIR /app

# Copy application code
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]
```

### 3.2. Docker Compose (개발용)

```yaml
version: '3.8'

services:
  user-service:
    build: .
    ports:
      - \"8000:8000\"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/aegis_user
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - postgres
      - redis
      - kafka
    volumes:
      - ./logs:/app/logs
    networks:
      - aegis-network

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=aegis_user
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - \"5432:5432\"
    networks:
      - aegis-network

  redis:
    image: redis:7-alpine
    ports:
      - \"6379:6379\"
    volumes:
      - redis_data:/data
    networks:
      - aegis-network

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
    depends_on:
      - zookeeper
    ports:
      - \"9092:9092\"
    networks:
      - aegis-network

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      - ZOOKEEPER_CLIENT_PORT=2181
      - ZOOKEEPER_TICK_TIME=2000
    networks:
      - aegis-network

volumes:
  postgres_data:
  redis_data:

networks:
  aegis-network:
    driver: bridge
```

## 4. Kubernetes 배포

### 4.1. Namespace 생성

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-user-service
  labels:
    app: aegis
    service: user-service
```

### 4.2. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
  namespace: aegis-user-service
data:
  # Application configuration
  LOG_LEVEL: \"INFO\"
  ENVIRONMENT: \"production\"
  
  # Database configuration
  DB_HOST: \"postgres-service\"
  DB_PORT: \"5432\"
  DB_NAME: \"aegis_user\"
  
  # Redis configuration
  REDIS_HOST: \"redis-service\"
  REDIS_PORT: \"6379\"
  
  # Kafka configuration
  KAFKA_BOOTSTRAP_SERVERS: \"kafka-service:9092\"
  
  # External API endpoints
  BUSINESS_REGISTRY_API_URL: \"https://api.odcloud.kr/api\"
  EMAIL_SERVICE_URL: \"https://api.sendgrid.com\"
  SMS_SERVICE_URL: \"https://api.twilio.com\"
```

### 4.3. Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: user-service-secrets
  namespace: aegis-user-service
type: Opaque
data:
  # Database credentials (base64 encoded)
  DB_USER: dXNlcg==  # user
  DB_PASSWORD: cGFzc3dvcmQ=  # password
  
  # JWT secrets
  JWT_SECRET_KEY: eW91ci1qd3Qtc2VjcmV0LWtleQ==
  JWT_REFRESH_SECRET_KEY: eW91ci1yZWZyZXNoLXNlY3JldA==
  
  # External API keys
  BUSINESS_REGISTRY_API_KEY: eW91ci1idXNpbmVzcy1hcGkta2V5
  EMAIL_API_KEY: eW91ci1lbWFpbC1hcGkta2V5
  SMS_API_KEY: eW91ci1zbXMtYXBpLWtleQ==
```

### 4.4. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  namespace: aegis-user-service
  labels:
    app: user-service
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
        version: v1.0.0
    spec:
      containers:
      - name: user-service
        image: aegis/user-service:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          value: \"postgresql://$(DB_USER):$(DB_PASSWORD)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)\"
        - name: REDIS_URL
          value: \"redis://$(REDIS_HOST):$(REDIS_PORT)/0\"
        envFrom:
        - configMapRef:
            name: user-service-config
        - secretRef:
            name: user-service-secrets
        resources:
          requests:
            memory: \"2Gi\"
            cpu: \"1000m\"
          limits:
            memory: \"4Gi\"
            cpu: \"2000m\"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
      restartPolicy: Always
```

### 4.5. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: aegis-user-service
  labels:
    app: user-service
spec:
  selector:
    app: user-service
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

### 4.6. Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: user-service-ingress
  namespace: aegis-user-service
  annotations:
    kubernetes.io/ingress.class: \"nginx\"
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: \"true\"
    cert-manager.io/cluster-issuer: \"letsencrypt-prod\"
spec:
  tls:
  - hosts:
    - api.aegis.example.com
    secretName: aegis-tls
  rules:
  - host: api.aegis.example.com
    http:
      paths:
      - path: /api/v1/users
        pathType: Prefix
        backend:
          service:
            name: user-service
            port:
              number: 80
```

### 4.7. HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: user-service-hpa
  namespace: aegis-user-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  minReplicas: 3
  maxReplicas: 10
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

## 5. 데이터베이스 배포

### 5.1. PostgreSQL StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: aegis-user-service
spec:
  serviceName: postgres-service
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
        env:
        - name: POSTGRES_DB
          value: \"aegis_user\"
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: user-service-secrets
              key: DB_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: user-service-secrets
              key: DB_PASSWORD
        - name: PGDATA
          value: \"/var/lib/postgresql/data/pgdata\"
        ports:
        - containerPort: 5432
          name: postgres
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        - name: postgres-config
          mountPath: /etc/postgresql/postgresql.conf
          subPath: postgresql.conf
        resources:
          requests:
            memory: \"2Gi\"
            cpu: \"1000m\"
          limits:
            memory: \"4Gi\"
            cpu: \"2000m\"
      volumes:
      - name: postgres-config
        configMap:
          name: postgres-config
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [\"ReadWriteOnce\"]
      resources:
        requests:
          storage: 100Gi
      storageClassName: fast-ssd
```

### 5.2. PostgreSQL Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: aegis-user-service
spec:
  selector:
    app: postgres
  ports:
  - name: postgres
    port: 5432
    targetPort: 5432
  type: ClusterIP
```

### 5.3. 데이터베이스 마이그레이션 Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: aegis-user-service
spec:
  template:
    spec:
      containers:
      - name: migration
        image: aegis/user-service:v1.0.0
        command: [\"python\", \"manage.py\", \"migrate\"]
        env:
        - name: DATABASE_URL
          value: \"postgresql://$(DB_USER):$(DB_PASSWORD)@postgres-service:5432/$(DB_NAME)\"
        envFrom:
        - configMapRef:
            name: user-service-config
        - secretRef:
            name: user-service-secrets
      restartPolicy: OnFailure
  backoffLimit: 3
```

## 6. 모니터링 설정

### 6.1. Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: user-service-monitor
  namespace: aegis-user-service
  labels:
    app: user-service
spec:
  selector:
    matchLabels:
      app: user-service
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
```

### 6.2. Grafana Dashboard 설정

```json
{
  \"dashboard\": {
    \"id\": null,
    \"title\": \"User Service Dashboard\",
    \"tags\": [\"aegis\", \"user-service\"],
    \"timezone\": \"browser\",
    \"panels\": [
      {
        \"id\": 1,
        \"title\": \"Request Rate\",
        \"type\": \"graph\",
        \"targets\": [
          {
            \"expr\": \"rate(http_requests_total{service=\\\"user-service\\\"}[5m])\",
            \"legendFormat\": \"{{method}} {{endpoint}}\"
          }
        ]
      },
      {
        \"id\": 2,
        \"title\": \"Response Time\",
        \"type\": \"graph\",
        \"targets\": [
          {
            \"expr\": \"histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\\\"user-service\\\"}[5m]))\",
            \"legendFormat\": \"95th percentile\"
          }
        ]
      },
      {
        \"id\": 3,
        \"title\": \"Error Rate\",
        \"type\": \"graph\",
        \"targets\": [
          {
            \"expr\": \"rate(http_requests_total{service=\\\"user-service\\\",status=~\\\"5..\\\"}[5m])\",
            \"legendFormat\": \"5xx errors\"
          }
        ]
      }
    ]
  }
}
```

### 6.3. 알림 규칙

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: user-service-alerts
  namespace: aegis-user-service
spec:
  groups:
  - name: user-service
    rules:
    - alert: UserServiceHighErrorRate
      expr: rate(http_requests_total{service=\"user-service\",status=~\"5..\"}[5m]) > 0.1
      for: 5m
      labels:
        severity: critical
        service: user-service
      annotations:
        summary: \"High error rate in User Service\"
        description: \"User Service error rate is {{ $value }} errors per second\"
    
    - alert: UserServiceHighLatency
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"user-service\"}[5m])) > 1
      for: 5m
      labels:
        severity: warning
        service: user-service
      annotations:
        summary: \"High latency in User Service\"
        description: \"User Service 95th percentile latency is {{ $value }}s\"
    
    - alert: UserServicePodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total{namespace=\"aegis-user-service\"}[15m]) > 0
      for: 5m
      labels:
        severity: critical
        service: user-service
      annotations:
        summary: \"User Service pod is crash looping\"
        description: \"Pod {{ $labels.pod }} is crash looping\"
```

## 7. 배포 스크립트

### 7.1. 배포 자동화 스크립트

```bash
#!/bin/bash

# User Service Deployment Script
set -e

# Configuration
NAMESPACE=\"aegis-user-service\"
IMAGE_TAG=${1:-\"latest\"}
ENVIRONMENT=${2:-\"production\"}

echo \"Deploying User Service v${IMAGE_TAG} to ${ENVIRONMENT}\"

# Create namespace if not exists
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply configurations
echo \"Applying configurations...\"
kubectl apply -f k8s/configmap.yaml -n ${NAMESPACE}
kubectl apply -f k8s/secrets.yaml -n ${NAMESPACE}

# Run database migrations
echo \"Running database migrations...\"
kubectl apply -f k8s/migration-job.yaml -n ${NAMESPACE}
kubectl wait --for=condition=complete job/db-migration -n ${NAMESPACE} --timeout=300s

# Deploy application
echo \"Deploying application...\"
sed \"s/{{IMAGE_TAG}}/${IMAGE_TAG}/g\" k8s/deployment.yaml | kubectl apply -f - -n ${NAMESPACE}
kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
kubectl apply -f k8s/ingress.yaml -n ${NAMESPACE}
kubectl apply -f k8s/hpa.yaml -n ${NAMESPACE}

# Wait for rollout to complete
echo \"Waiting for deployment to complete...\"
kubectl rollout status deployment/user-service -n ${NAMESPACE} --timeout=600s

# Verify deployment
echo \"Verifying deployment...\"
kubectl get pods -n ${NAMESPACE} -l app=user-service

# Run health check
echo \"Running health check...\"
SERVICE_URL=$(kubectl get ingress user-service-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}')
curl -f https://${SERVICE_URL}/health || {
    echo \"Health check failed!\"
    exit 1
}

echo \"Deployment completed successfully!\"
```

### 7.2. 롤백 스크립트

```bash
#!/bin/bash

# User Service Rollback Script
set -e

NAMESPACE=\"aegis-user-service\"
REVISION=${1:-\"previous\"}

echo \"Rolling back User Service to revision: ${REVISION}\"

# Rollback deployment
if [ \"${REVISION}\" = \"previous\" ]; then
    kubectl rollout undo deployment/user-service -n ${NAMESPACE}
else
    kubectl rollout undo deployment/user-service --to-revision=${REVISION} -n ${NAMESPACE}
fi

# Wait for rollback to complete
kubectl rollout status deployment/user-service -n ${NAMESPACE} --timeout=600s

# Verify rollback
kubectl get pods -n ${NAMESPACE} -l app=user-service

echo \"Rollback completed successfully!\"
```

## 8. 환경별 설정

### 8.1. 개발 환경 설정

```yaml
# dev-values.yaml
replicaCount: 1

image:
  repository: aegis/user-service
  tag: dev
  pullPolicy: Always

resources:
  requests:
    memory: \"512Mi\"
    cpu: \"250m\"
  limits:
    memory: \"1Gi\"
    cpu: \"500m\"

database:
  host: \"postgres-dev\"
  name: \"aegis_user_dev\"

redis:
  host: \"redis-dev\"

kafka:
  bootstrapServers: \"kafka-dev:9092\"

ingress:
  enabled: true
  host: \"dev-api.aegis.example.com\"

monitoring:
  enabled: false
```

### 8.2. 프로덕션 환경 설정

```yaml
# prod-values.yaml
replicaCount: 3

image:
  repository: aegis/user-service
  tag: v1.0.0
  pullPolicy: IfNotPresent

resources:
  requests:
    memory: \"2Gi\"
    cpu: \"1000m\"
  limits:
    memory: \"4Gi\"
    cpu: \"2000m\"

database:
  host: \"postgres-prod\"
  name: \"aegis_user\"

redis:
  host: \"redis-cluster\"

kafka:
  bootstrapServers: \"kafka-cluster:9092\"

ingress:
  enabled: true
  host: \"api.aegis.example.com\"
  tls:
    enabled: true

monitoring:
  enabled: true

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

## 9. 보안 설정

### 9.1. Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: user-service-network-policy
  namespace: aegis-user-service
spec:
  podSelector:
    matchLabels:
      app: user-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: aegis-database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          name: aegis-cache
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS outbound
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

### 9.2. Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: user-service-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## 10. 백업 및 복구

### 10.1. 데이터베이스 백업 CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: aegis-user-service
spec:
  schedule: \"0 2 * * *\"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              BACKUP_FILE=\"/backup/aegis_user_$(date +%Y%m%d_%H%M%S).sql\"
              pg_dump -h postgres-service -U $POSTGRES_USER -d aegis_user > $BACKUP_FILE
              echo \"Backup completed: $BACKUP_FILE\"
            env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: user-service-secrets
                  key: DB_USER
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: user-service-secrets
                  key: DB_PASSWORD
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

이제 USER_SERVICE의 배포 가이드가 완성되었습니다!

---

**📋 관련 문서**
- [사용자 서비스 API 명세](./01_API_SPECS.md)
- [사용자 서비스 통합 명세](./06_INTEGRATION_SPECS.md)
- [사용자 서비스 테스트 전략](./08_TESTING_STRATEGY.md)