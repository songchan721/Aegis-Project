# Infrastructure Setup Design Document (v2.1)

**Version**: 2.1  
**Date**: 2025-10-08  
**Status**: Finalized  
**Authors**: Kiro AI

## 1. Overview

이지스(Aegis) 인프라는 Kubernetes 기반의 클라우드 네이티브 아키텍처로 설계되며, 고가용성, 확장성, 보안성을 보장하는 프로덕션 레디 환경을 제공합니다.

**핵심 책임**:
- 클라우드 독립적인 Kubernetes 클러스터 관리
- 모든 애플리케이션 서비스를 위한 플랫폼 제공
- 데이터베이스, 메시징, 캐싱 등 인프라 서비스 운영
- 모니터링, 로깅, 보안 등 플랫폼 서비스 제공
- Infrastructure as Code(IaC) 및 GitOps 기반 자동화

**설계 원칙**:
- **클라우드 독립성**: AWS, GCP, Azure 등 어떤 클라우드에서도 동작 (`AEGIS_SPECIFICATION` 원칙).
- **선언적 관리**: 모든 인프라는 코드로 정의되고 버전 관리됩니다 (GitOps).
- **자동화 우선**: 수동 작업을 최소화하고, 자동 복구 및 스케일링을 지향합니다 (`AEGIS_SPECIFICATION`의 '살아있는 게이트웨이' 원칙 지원).
- **보안 기본**: Zero Trust 네트워크, 최소 권한 원칙을 적용합니다 (`AEGIS_SPECIFICATION`의 '데이터 무결성' 원칙 지원).
- **관찰성**: 모든 계층에서 메트릭, 로그, 추적을 수집하여 시스템 상태를 명확히 파악합니다.

## 2. Shared Library Integration

인프라는 `aegis-shared` 공통 라이브러리가 원활하게 동작하는 데 필요한 모든 백엔드 서비스를 제공하고, 서비스 간의 안정적인 통신을 보장합니다.

### 2.1. 제공 인프라 서비스

| 서비스 | 용도 | `shared-library` 모듈 | 연결 방법 | 포트 |
|---|---|---|---|---|
| PostgreSQL | 관계형 데이터베이스 | `database` | Kubernetes Service DNS | 5432 |
| Redis | 캐싱 및 세션 | `cache` | Kubernetes Service DNS | 6379 |
| Kafka (KRaft) | 이벤트 메시징 | `messaging` | Kubernetes Service DNS | 9092 (plain), 9093 (tls) |
| Schema Registry | 이벤트 스키마 관리 | `messaging.schema_registry` | Kubernetes Service DNS | 8081 |
| Elasticsearch | 로그 저장소 | `logging` | Filebeat → Logstash | 9200 |
| Prometheus | 메트릭 수집 | `monitoring` | ServiceMonitor | 9090 |
| Milvus | 벡터 검색 | `search` (향후) | Kubernetes Service DNS | 19530 |
| Neo4j | 그래프 데이터베이스 | `graph` (향후) | Kubernetes Service DNS | 7687 (bolt), 7474 (http) |

### 2.2. 서비스 디스커버리

애플리케이션은 Kubernetes의 DNS 기반 서비스 디스커버리를 통해 인프라 서비스에 접근합니다. 이를 통해 서비스의 물리적 위치(IP 주소)가 변경되더라도 코드 수정 없이 유연하게 연결을 유지할 수 있습니다.

**Before (Hardcoded IP):**
```python
# 직접 IP 주소 사용 (취약하고 경직된 방식)
DATABASE_URL = "postgresql://user:pass@10.20.30.40:5432/aegis"
```

**After (Kubernetes Service DNS):**
```python
# 환경 변수와 K8s 서비스를 통한 동적 연결 (권장)
# 서비스 주소: {service-name}.{namespace}.svc.cluster.local
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:pass@postgresql.aegis-data.svc.cluster.local:5432/aegis"
)
```

### 2.3. Shared Library 요구사항 충족

#### 2.3.1. 데이터베이스 연결 (Requirement 1)

인프라는 PostgreSQL Operator를 통해 고가용성 데이터베이스 클러스터를 제공합니다:
- **연결 풀링**: PgBouncer를 통한 연결 풀 관리
- **자동 페일오버**: 마스터 장애 시 자동으로 슬레이브 승격
- **백업 및 복구**: 자동 백업 및 PITR (Point-In-Time Recovery)

```yaml
# 애플리케이션 ConfigMap 예시
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
  namespace: aegis-production
data:
  DATABASE_URL: "postgresql://aegis_user:${DB_PASSWORD}@postgresql.aegis-data.svc.cluster.local:5432/aegis"
  DATABASE_POOL_SIZE: "10"
  DATABASE_MAX_OVERFLOW: "20"
```

#### 2.3.2. 인증 및 인가 (Requirement 2)

Istio 서비스 메시를 통해 자동 mTLS 및 JWT 검증을 지원합니다:
- **자동 mTLS**: 모든 서비스 간 통신 암호화
- **JWT 검증**: Istio RequestAuthentication을 통한 토큰 검증
- **RBAC**: Istio AuthorizationPolicy를 통한 세밀한 접근 제어

```yaml
# JWT 검증 정책
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: aegis-production
spec:
  jwtRules:
  - issuer: "https://auth.aegis.example.com"
    jwksUri: "https://auth.aegis.example.com/.well-known/jwks.json"
```

#### 2.3.3. 구조화된 로깅 (Requirement 3)

ELK Stack을 통해 중앙화된 로그 수집 및 분석을 제공합니다:
- **자동 수집**: Filebeat가 모든 Pod 로그 자동 수집
- **구조화**: Logstash가 JSON 로그 파싱 및 인덱싱
- **검색**: Kibana를 통한 실시간 로그 검색 및 시각화

```yaml
# Filebeat 자동 수집 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: logging
data:
  filebeat.yml: |
    filebeat.autodiscover:
      providers:
        - type: kubernetes
          node: ${NODE_NAME}
          hints.enabled: true
          hints.default_config:
            type: container
            paths:
              - /var/log/containers/*${data.kubernetes.container.id}.log
    
    processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
          - logs_path:
              logs_path: "/var/log/containers/"
      - decode_json_fields:
          fields: ["message"]
          target: ""
          overwrite_keys: true
```

#### 2.3.4. 이벤트 발행 및 구독 (Requirement 4)

Kafka (KRaft 모드) 및 Schema Registry를 통해 안정적인 이벤트 스트리밍을 제공합니다:
- **KRaft 모드**: Zookeeper 없이 Kafka 자체 메타데이터 관리
- **Schema Registry**: Avro 스키마 진화 및 호환성 관리
- **고가용성**: 3개 브로커로 데이터 복제

```python
# shared-library에서 사용 예시
from aegis_shared.messaging import EventPublisher

publisher = EventPublisher(
    bootstrap_servers="aegis-kafka-bootstrap.aegis-data.svc.cluster.local:9092",
    schema_registry_url="http://schema-registry.aegis-data.svc.cluster.local:8081"
)

await publisher.publish(
    topic="user.events",
    event_type="user.created",
    data={"user_id": "user-123", "email": "test@example.com"}
)
```

#### 2.3.5. 모니터링 및 메트릭 (Requirement 6)

Prometheus 및 Grafana를 통해 포괄적인 모니터링을 제공합니다:
- **자동 수집**: ServiceMonitor를 통한 메트릭 자동 수집
- **분산 추적**: Istio + Jaeger를 통한 요청 추적
- **대시보드**: 사전 구성된 Grafana 대시보드

```yaml
# ServiceMonitor 자동 생성
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: user-service
  namespace: aegis-production
spec:
  selector:
    matchLabels:
      app: user-service
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

#### 2.3.6. 캐싱 (Requirement 8)

Redis Cluster를 통해 고성능 캐싱을 제공합니다:
- **클러스터 모드**: 샤딩을 통한 수평 확장
- **고가용성**: 센티넬 모드로 자동 페일오버
- **영속성**: AOF 및 RDB 스냅샷

```python
# shared-library에서 사용 예시
from aegis_shared.cache import RedisClient

cache = RedisClient(
    host="aegis-redis.aegis-data.svc.cluster.local",
    port=6379,
    cluster_mode=True
)

@cache.cached(ttl=3600)
async def get_user(user_id: str):
    # 캐시 미스 시 데이터베이스 조회
    return await db.get_user(user_id)
```

#### 2.3.7. 환경 설정 관리 (Requirement 9)

External Secrets Operator를 통해 안전한 시크릿 관리를 제공합니다:
- **외부 통합**: AWS Secrets Manager, Vault 등과 연동
- **자동 동기화**: 시크릿 변경 시 자동 업데이트
- **암호화**: 전송 및 저장 시 암호화

```yaml
# ExternalSecret 사용 예시
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: user-service-secrets
  namespace: aegis-production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: user-service-secrets
  data:
  - secretKey: DATABASE_PASSWORD
    remoteRef:
      key: aegis/user-service/database
      property: password
  - secretKey: JWT_SECRET
    remoteRef:
      key: aegis/user-service/jwt
      property: secret
```

#### 2.3.8. 중앙 스키마 레지스트리 (Requirement 11)

인프라는 스키마 파일을 Git 저장소에 저장하고 ArgoCD를 통해 배포합니다:
- **버전 관리**: Git을 통한 스키마 버전 관리
- **자동 배포**: ArgoCD가 스키마 변경 감지 및 배포
- **검증**: CI 파이프라인에서 스키마 무결성 검증

```yaml
# ArgoCD Application for Schema Registry
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: schema-registry
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://gitlab.aegis.example.com/aegis/schemas.git
    targetRevision: main
    path: schemas
  destination:
    server: https://kubernetes.default.svc
    namespace: aegis-data
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 2.4. 서비스 간 통신 패턴

```mermaid
sequenceDiagram
    participant App as Application Service
    participant Istio as Istio Sidecar
    participant DB as PostgreSQL
    participant Cache as Redis
    participant Kafka as Kafka
    participant Prom as Prometheus
    
    App->>Istio: Request with JWT
    Istio->>Istio: Verify JWT
    Istio->>Istio: Apply mTLS
    
    App->>Cache: Check Cache
    alt Cache Hit
        Cache-->>App: Return Data
    else Cache Miss
        App->>DB: Query Database
        DB-->>App: Return Data
        App->>Cache: Update Cache
    end
    
    App->>Kafka: Publish Event
    Kafka-->>App: Ack
    
    Istio->>Prom: Export Metrics
    App->>Prom: Export Custom Metrics
```

## 3. Architecture

### 3.1. 전체 인프라 아키텍처

```mermaid
graph TB
    subgraph "External"
        USERS[Users]
        DEVS[Developers]
    end
    subgraph "Edge Layer"
        CDN[CloudFlare CDN]
        WAF[Web Application Firewall]
        LB[Load Balancer]
    end
    subgraph "Kubernetes Cluster"
        subgraph "Ingress Layer"
            NGINX[NGINX Ingress]
            ISTIO_GW[Istio Gateway]
        end
        subgraph "Service Mesh"
            ISTIO[Istio Service Mesh]
        end
        subgraph "Application Namespaces"
            PROD_NS[Production Namespace]
            STAGING_NS[Staging Namespace]
        end
        subgraph "Platform Services"
            MONITORING[Monitoring Stack]
            LOGGING[Logging Stack]
            SECURITY[Security Stack]
        end
        subgraph "Data Layer"
            POSTGRES_OP[PostgreSQL Operator]
            REDIS_OP[Redis Operator]
            KAFKA_OP[Kafka Operator]
        end
    end
    subgraph "CI/CD"
        GITLAB[GitLab CI/CD]
        ARGOCD[ArgoCD]
    end
    USERS --> CDN --> WAF --> LB --> NGINX --> ISTIO_GW --> ISTIO --> PROD_NS
    DEVS --> GITLAB --> ARGOCD --> PROD_NS
    DEVS --> GITLAB --> ARGOCD --> STAGING_NS
```

### 3.2. 클러스터 아키텍처

```mermaid
graph TB
    subgraph "Control Plane (Multi-AZ)"
        MASTER1[Master Node 1 (AZ-A)]
        MASTER2[Master Node 2 (AZ-B)]
        MASTER3[Master Node 3 (AZ-C)]
        ETCD[etcd Cluster]
    end
    subgraph "Worker Nodes (Multi-AZ)"
        subgraph "Application Nodes"
            APP1[App Node (AZ-A)]
            APP2[App Node (AZ-B)]
            APP3[App Node (AZ-C)]
        end
        subgraph "Data Nodes"
            DATA1[Data Node (AZ-A)]
            DATA2[Data Node (AZ-B)]
            DATA3[Data Node (AZ-C)]
        end
        subgraph "Platform Nodes"
            PLATFORM1[Platform Node (AZ-A)]
            PLATFORM2[Platform Node (AZ-B)]
        end
    end
    MASTER1 & MASTER2 & MASTER3 --> ETCD
    MASTER1 & MASTER2 & MASTER3 --> APP1 & APP2 & APP3
    MASTER1 & MASTER2 & MASTER3 --> DATA1 & DATA2 & DATA3
    MASTER1 & MASTER2 & MASTER3 --> PLATFORM1 & PLATFORM2
```

### 3.3. 데이터 흐름

```mermaid
sequenceDiagram
    participant User
    participant Ingress
    participant ServiceMesh
    participant App
    participant DB
    participant Cache
    participant Kafka
    
    User->>Ingress: HTTPS Request
    Ingress->>ServiceMesh: Route to Service
    ServiceMesh->>App: mTLS Connection
    App->>Cache: Check Cache
    alt Cache Hit
        Cache-->>App: Return Data
    else Cache Miss
        App->>DB: Query Database
        DB-->>App: Return Data
        App->>Cache: Update Cache
    end
    App->>Kafka: Publish Event (e.g., user.created)
    App-->>ServiceMesh: Response
    ServiceMesh-->>Ingress: Response
    Ingress-->>User: HTTPS Response
```

## 4. Components and Interfaces

### 4.1. Kubernetes 클러스터 구성

#### 4.1.1. 클러스터 사양 (클라우드 독립적)

```yaml
# cluster-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-config
data:
  cluster-name: "aegis-production"
  kubernetes-version: "1.28.0"
  
  control-plane:
    replicas: 3
    instance-type-aws: "t3.medium"
    instance-type-gcp: "n1-standard-2"
    disk-size: "50Gi"
    
  worker-nodes:
    application-nodes:
      min-size: 3
      max-size: 10
      instance-type-aws: "t3.large"
      disk-size: "100Gi"
    data-nodes:
      min-size: 3
      max-size: 6
      instance-type-aws: "r5.xlarge"
      disk-size: "500Gi"
      storage-optimized: true
```

### 4.2. 서비스 메시 구성 (Istio)

```yaml
# istio-config.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: aegis-istio
spec:
  values:
    global:
      meshID: aegis-mesh
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 200m
            memory: 128Mi
    ingressGateways:
    - name: istio-ingressgateway
      enabled: true
      k8s:
        service:
          type: LoadBalancer
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
```

### 4.3. 모니터링 스택 (Prometheus + Grafana)

```yaml
# prometheus-config.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: aegis-prometheus
  namespace: monitoring
spec:
  replicas: 2
  retention: "30d"
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 100Gi
  serviceMonitorSelector:
    matchLabels:
      team: aegis
```

### 4.4. 로깅 스택 (ELK)

```yaml
# logstash-pipeline.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: logstash-pipeline
  namespace: logging
data:
  logstash.conf: |
    input {
      beats {
        port => 5044
      }
    }
    filter {
      json {
        source => "message"
      }
      mutate {
        gsub => [
          "message", "password=\S+", "password=***MASKED***"
        ]
      }
    }
    output {
      elasticsearch {
        hosts => ["aegis-elasticsearch-es-http:9200"]
        index => "aegis-logs-%{+YYYY.MM.dd}"
      }
    }
```

### 4.5. PostgreSQL Operator 구성

```yaml
# postgresql-cluster.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: aegis-postgresql
  namespace: aegis-data
spec:
  instances: 3
  imageName: ghcr.io/cloudnative-pg/postgresql:15.3
  
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      maintenance_work_mem: "64MB"
      checkpoint_completion_target: "0.9"
      wal_buffers: "16MB"
      default_statistics_target: "100"
      random_page_cost: "1.1"
      effective_io_concurrency: "200"
      work_mem: "2621kB"
      min_wal_size: "1GB"
      max_wal_size: "4GB"
  
  bootstrap:
    initdb:
      database: aegis
      owner: aegis_user
      secret:
        name: aegis-postgresql-credentials
  
  storage:
    size: 100Gi
    storageClass: fast-ssd
  
  backup:
    barmanObjectStore:
      destinationPath: s3://aegis-backups/postgresql
      s3Credentials:
        accessKeyId:
          name: aws-credentials
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: aws-credentials
          key: SECRET_ACCESS_KEY
      wal:
        compression: gzip
        maxParallel: 8
    retentionPolicy: "30d"
  
  monitoring:
    enablePodMonitor: true
  
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: cnpg.io/cluster
            operator: In
            values:
            - aegis-postgresql
        topologyKey: topology.kubernetes.io/zone
```

### 4.6. Redis Operator 구성

```yaml
# redis-cluster.yaml
apiVersion: redis.redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: aegis-redis
  namespace: aegis-data
spec:
  clusterSize: 3
  clusterVersion: v7
  
  redisLeader:
    replicas: 3
    redisConfig:
      maxmemory: "2gb"
      maxmemory-policy: "allkeys-lru"
      save: "900 1 300 10 60 10000"
      appendonly: "yes"
      appendfsync: "everysec"
    
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 1000m
        memory: 2Gi
    
    storage:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          storageClassName: fast-ssd
          resources:
            requests:
              storage: 10Gi
    
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app: aegis-redis
          topologyKey: topology.kubernetes.io/zone
  
  redisFollower:
    replicas: 3
    redisConfig:
      maxmemory: "2gb"
      maxmemory-policy: "allkeys-lru"
      slave-read-only: "yes"
    
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 1000m
        memory: 2Gi
  
  monitoring:
    enabled: true
    image: oliver006/redis_exporter:latest
```

### 4.7. Kafka Operator 구성 (Strimzi) - KRaft 모드

```yaml
# kafka-cluster.yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: aegis-kafka
  namespace: aegis-data
spec:
  kafka:
    version: 3.6.0
    replicas: 3
    
    # KRaft 모드 활성화 (Zookeeper 제거)
    metadataVersion: 3.6-IV2
    
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: tls
      - name: external
        port: 9094
        type: loadbalancer
        tls: true
        authentication:
          type: tls
    
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
      log.retention.hours: 168
      log.segment.bytes: 1073741824
      log.retention.check.interval.ms: 300000
      num.network.threads: 8
      num.io.threads: 8
      socket.send.buffer.bytes: 102400
      socket.receive.buffer.bytes: 102400
      socket.request.max.bytes: 104857600
      # KRaft 전용 설정
      node.id.generation.enable: true
      process.roles: broker,controller
      controller.quorum.voters: 0@aegis-kafka-0:9093,1@aegis-kafka-1:9093,2@aegis-kafka-2:9093
    
    storage:
      type: jbod
      volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: fast-ssd
        deleteClaim: false
    
    resources:
      requests:
        memory: 4Gi
        cpu: 1000m
      limits:
        memory: 4Gi
        cpu: 2000m
    
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
    
    rack:
      topologyKey: topology.kubernetes.io/zone
  
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

### 4.7.1. Kafka Schema Registry 구성

```yaml
# schema-registry.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: schema-registry
  namespace: aegis-data
spec:
  replicas: 2
  selector:
    matchLabels:
      app: schema-registry
  template:
    metadata:
      labels:
        app: schema-registry
    spec:
      containers:
      - name: schema-registry
        image: confluentinc/cp-schema-registry:7.5.0
        ports:
        - containerPort: 8081
        env:
        - name: SCHEMA_REGISTRY_HOST_NAME
          value: schema-registry
        - name: SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS
          value: "aegis-kafka-bootstrap:9092"
        - name: SCHEMA_REGISTRY_LISTENERS
          value: "http://0.0.0.0:8081"
        - name: SCHEMA_REGISTRY_KAFKASTORE_TOPIC
          value: "_schemas"
        - name: SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR
          value: "3"
        - name: SCHEMA_REGISTRY_SCHEMA_COMPATIBILITY_LEVEL
          value: "BACKWARD"
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 8081
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: schema-registry
  namespace: aegis-data
spec:
  selector:
    app: schema-registry
  ports:
  - port: 8081
    targetPort: 8081
  type: ClusterIP
```

### 4.8. ArgoCD 구성

```yaml
# argocd-config.yaml
apiVersion: argoproj.io/v1alpha1
kind: ArgoCD
metadata:
  name: aegis-argocd
  namespace: argocd
spec:
  server:
    replicas: 2
    
    ingress:
      enabled: true
      ingressClassName: nginx
      annotations:
        cert-manager.io/cluster-issuer: letsencrypt-prod
      hosts:
      - argocd.aegis.example.com
      tls:
      - secretName: argocd-tls
        hosts:
        - argocd.aegis.example.com
    
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
  
  repo:
    replicas: 2
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
  
  controller:
    replicas: 1
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: 1000m
        memory: 2Gi
  
  dex:
    openShiftOAuth: false
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 200m
        memory: 256Mi
  
  redis:
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 200m
        memory: 256Mi
  
  ha:
    enabled: true
    redisProxyImage: haproxy
    redisProxyVersion: "2.6.2"
  
  rbac:
    defaultPolicy: 'role:readonly'
    policy: |
      g, aegis-admins, role:admin
      g, aegis-developers, role:developer
    scopes: '[groups]'
```

### 4.9. Milvus 벡터 데이터베이스 구성

```yaml
# milvus-cluster.yaml
apiVersion: milvus.io/v1beta1
kind: Milvus
metadata:
  name: aegis-milvus
  namespace: aegis-data
spec:
  mode: cluster
  
  dependencies:
    etcd:
      inCluster:
        deletionPolicy: Retain
        pvcDeletion: false
        values:
          replicaCount: 3
          persistence:
            storageClass: fast-ssd
            size: 10Gi
    
    pulsar:
      inCluster:
        deletionPolicy: Retain
        pvcDeletion: false
        values:
          broker:
            replicaCount: 2
          bookkeeper:
            replicaCount: 3
            persistence:
              storageClass: fast-ssd
              size: 50Gi
    
    storage:
      inCluster:
        deletionPolicy: Retain
        pvcDeletion: false
        values:
          mode: distributed
          persistence:
            storageClass: fast-ssd
            size: 100Gi
  
  components:
    proxy:
      replicas: 2
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 1000m
          memory: 2Gi
    
    rootCoord:
      replicas: 1
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 1000m
          memory: 2Gi
    
    queryCoord:
      replicas: 1
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 1000m
          memory: 2Gi
    
    queryNode:
      replicas: 2
      resources:
        requests:
          cpu: 2000m
          memory: 8Gi
        limits:
          cpu: 4000m
          memory: 16Gi
    
    indexCoord:
      replicas: 1
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 1000m
          memory: 2Gi
    
    indexNode:
      replicas: 2
      resources:
        requests:
          cpu: 2000m
          memory: 4Gi
        limits:
          cpu: 4000m
          memory: 8Gi
    
    dataCoord:
      replicas: 1
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 1000m
          memory: 2Gi
    
    dataNode:
      replicas: 2
      resources:
        requests:
          cpu: 1000m
          memory: 2Gi
        limits:
          cpu: 2000m
          memory: 4Gi
  
  config:
    common:
      retentionDuration: 432000  # 5일
    
    queryNode:
      gracefulTime: 1000
      cacheSize: 32  # GB
    
    indexNode:
      enableDisk: true
```

### 4.10. Neo4j 그래프 데이터베이스 구성

```yaml
# neo4j-cluster.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: neo4j-config
  namespace: aegis-data
data:
  neo4j.conf: |
    dbms.mode=CORE
    causal_clustering.minimum_core_cluster_size_at_formation=3
    causal_clustering.minimum_core_cluster_size_at_runtime=3
    causal_clustering.initial_discovery_members=neo4j-0.neo4j.aegis-data.svc.cluster.local:5000,neo4j-1.neo4j.aegis-data.svc.cluster.local:5000,neo4j-2.neo4j.aegis-data.svc.cluster.local:5000
    dbms.connector.bolt.listen_address=0.0.0.0:7687
    dbms.connector.http.listen_address=0.0.0.0:7474
    dbms.memory.heap.initial_size=2g
    dbms.memory.heap.max_size=4g
    dbms.memory.pagecache.size=2g
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
  namespace: aegis-data
spec:
  serviceName: neo4j
  replicas: 3
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.13-enterprise
        ports:
        - containerPort: 7474
          name: http
        - containerPort: 7687
          name: bolt
        - containerPort: 5000
          name: discovery
        - containerPort: 6000
          name: tx
        - containerPort: 7000
          name: raft
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: auth
        - name: NEO4J_ACCEPT_LICENSE_AGREEMENT
          value: "yes"
        - name: NEO4J_dbms_mode
          value: "CORE"
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /conf
        resources:
          requests:
            cpu: 1000m
            memory: 4Gi
          limits:
            cpu: 2000m
            memory: 8Gi
      volumes:
      - name: config
        configMap:
          name: neo4j-config
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: neo4j
  namespace: aegis-data
spec:
  clusterIP: None
  selector:
    app: neo4j
  ports:
  - port: 7474
    name: http
  - port: 7687
    name: bolt
  - port: 5000
    name: discovery
  - port: 6000
    name: tx
  - port: 7000
    name: raft
---
apiVersion: v1
kind: Service
metadata:
  name: neo4j-lb
  namespace: aegis-data
spec:
  type: LoadBalancer
  selector:
    app: neo4j
  ports:
  - port: 7474
    targetPort: 7474
    name: http
  - port: 7687
    targetPort: 7687
    name: bolt
```

### 4.11. External Secrets Operator 구성

```yaml
# external-secrets-operator.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: external-secrets
---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: aegis-production
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: aegis-database-credentials
  namespace: aegis-production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  
  target:
    name: database-credentials
    creationPolicy: Owner
    template:
      engineVersion: v2
      data:
        DATABASE_URL: "postgresql://{{ .username }}:{{ .password }}@postgresql.aegis-data.svc.cluster.local:5432/aegis"
  
  data:
  - secretKey: username
    remoteRef:
      key: aegis/database/credentials
      property: username
  - secretKey: password
    remoteRef:
      key: aegis/database/credentials
      property: password
---
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.aegis-security.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
```

### 4.12. OPA Gatekeeper 정책 구성

```yaml
# opa-gatekeeper-policies.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        
        violation[{"msg": msg, "details": {"missing_labels": missing}}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("필수 레이블이 누락되었습니다: %v", [missing])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-team-label
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - "aegis-production"
      - "aegis-staging"
  parameters:
    labels:
      - "team"
      - "app"
      - "environment"
---
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sblocklatestimage
spec:
  crd:
    spec:
      names:
        kind: K8sBlockLatestImage
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sblocklatestimage
        
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          endswith(container.image, ":latest")
          msg := sprintf("컨테이너 %v는 :latest 태그를 사용할 수 없습니다", [container.name])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sBlockLatestImage
metadata:
  name: block-latest-image
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet", "DaemonSet"]
    namespaces:
      - "aegis-production"
---
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequirenonroot
spec:
  crd:
    spec:
      names:
        kind: K8sRequireNonRoot
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequirenonroot
        
        violation[{"msg": msg}] {
          not input.review.object.spec.securityContext.runAsNonRoot
          msg := "컨테이너는 non-root 사용자로 실행되어야 합니다"
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequireNonRoot
metadata:
  name: require-non-root
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
    namespaces:
      - "aegis-production"
```

### 4.13. Cert-Manager 구성

```yaml
# cert-manager-config.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cert-manager
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@aegis.example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
    - dns01:
        route53:
          region: ap-northeast-2
          hostedZoneID: Z1234567890ABC
          accessKeyID: AKIAIOSFODNN7EXAMPLE
          secretAccessKeySecretRef:
            name: route53-credentials
            key: secret-access-key
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@aegis.example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: aegis-tls
  namespace: aegis-production
spec:
  secretName: aegis-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - aegis.example.com
  - "*.aegis.example.com"
  - api.aegis.example.com
  - argocd.aegis.example.com
  renewBefore: 720h  # 30일 전 갱신
```

### 4.14. VPA (Vertical Pod Autoscaler) 구성

```yaml
# vpa-config.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: user-service-vpa
  namespace: aegis-production
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: user-service
  
  updatePolicy:
    updateMode: "Auto"  # "Off", "Initial", "Recreate", "Auto"
  
  resourcePolicy:
    containerPolicies:
    - containerName: user-service
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2000m
        memory: 4Gi
      controlledResources:
      - cpu
      - memory
      mode: Auto
---
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: policy-service-vpa
  namespace: aegis-production
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: policy-service
  
  updatePolicy:
    updateMode: "Auto"
  
  resourcePolicy:
    containerPolicies:
    - containerName: policy-service
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2000m
        memory: 4Gi
      controlledResources:
      - cpu
      - memory
---
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: recommendation-service-vpa
  namespace: aegis-production
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: recommendation-service
  
  updatePolicy:
    updateMode: "Recreate"  # 추천 서비스는 재시작 허용
  
  resourcePolicy:
    containerPolicies:
    - containerName: recommendation-service
      minAllowed:
        cpu: 500m
        memory: 1Gi
      maxAllowed:
        cpu: 4000m
        memory: 16Gi
      controlledResources:
      - cpu
      - memory
```

### 4.15. Velero 백업 구성

```yaml
# velero-backup-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: aegis-daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 매일 02:00 KST
  
  template:
    includedNamespaces:
    - aegis-production
    - aegis-data
    - monitoring
    - logging
    
    excludedResources:
    - events
    - events.events.k8s.io
    
    storageLocation: default
    
    volumeSnapshotLocations:
    - default
    
    ttl: 720h  # 30일
    
    hooks:
      resources:
      - name: postgresql-backup
        includedNamespaces:
        - aegis-data
        labelSelector:
          matchLabels:
            app: postgresql
        pre:
        - exec:
            command:
            - /bin/bash
            - -c
            - pg_dump -U aegis_user aegis > /tmp/backup.sql
            container: postgresql
            onError: Fail
            timeout: 10m
---
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: default
  namespace: velero
spec:
  provider: aws
  objectStorage:
    bucket: aegis-velero-backups
    prefix: cluster-backups
  config:
    region: ap-northeast-2
  credential:
    name: cloud-credentials
    key: cloud
```

## 5. Data Models

### 5.1. 인프라 구성 데이터 모델

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    ON_PREMISE = "on-premise"

class NodeConfig(BaseModel):
    """노드 그룹 구성"""
    min_size: int = Field(ge=1, description="최소 노드 수")
    max_size: int = Field(ge=1, description="최대 노드 수")
    disk_size: str = Field(description="디스크 크기 (예: 100Gi)")
    instance_type: str = Field(description="인스턴스 타입")
    labels: Dict[str, str] = Field(default_factory=dict)
    taints: List[Dict[str, str]] = Field(default_factory=list)
    
    @validator('max_size')
    def max_greater_than_min(cls, v, values):
        if 'min_size' in values and v < values['min_size']:
            raise ValueError('max_size must be >= min_size')
        return v

class ClusterConfig(BaseModel):
    """Kubernetes 클러스터 구성"""
    cluster_name: str = Field(description="클러스터 이름")
    kubernetes_version: str = Field(description="Kubernetes 버전 (예: 1.28.0)")
    cloud_provider: CloudProvider
    region: str = Field(description="클라우드 리전")
    availability_zones: List[str] = Field(min_items=2, description="가용 영역 목록")
    node_configs: Dict[str, NodeConfig]
    
    # 네트워크 설정
    vpc_cidr: str = Field(default="10.0.0.0/16")
    pod_cidr: str = Field(default="10.244.0.0/16")
    service_cidr: str = Field(default="10.96.0.0/16")
    
    # 기능 플래그
    enable_istio: bool = Field(default=True)
    enable_monitoring: bool = Field(default=True)
    enable_logging: bool = Field(default=True)
    enable_backup: bool = Field(default=True)

class MonitoringConfig(BaseModel):
    """모니터링 스택 구성"""
    prometheus_retention: str = Field(default="30d")
    prometheus_storage_size: str = Field(default="100Gi")
    grafana_admin_password: str = Field(description="Grafana 관리자 비밀번호")
    alertmanager_config: Dict[str, any] = Field(default_factory=dict)
    
    # 알림 채널
    slack_webhook_url: Optional[str] = None
    pagerduty_service_key: Optional[str] = None
    email_recipients: List[str] = Field(default_factory=list)

class BackupConfig(BaseModel):
    """백업 구성"""
    enabled: bool = Field(default=True)
    schedule: str = Field(default="0 2 * * *", description="Cron 형식")
    retention_days: int = Field(default=30, ge=1)
    storage_location: str = Field(description="백업 저장 위치 (S3 버킷 등)")
    
    # 백업 대상
    include_namespaces: List[str] = Field(default_factory=list)
    exclude_resources: List[str] = Field(default_factory=list)
    
    # 복구 목표
    rto_hours: int = Field(default=2, description="Recovery Time Objective")
    rpo_minutes: int = Field(default=15, description="Recovery Point Objective")

class DisasterRecoveryConfig(BaseModel):
    """재해 복구 구성"""
    multi_region_enabled: bool = Field(default=False)
    primary_region: str
    dr_region: Optional[str] = None
    
    # 복제 설정
    database_replication: bool = Field(default=True)
    storage_replication: bool = Field(default=True)
    
    # 페일오버 설정
    auto_failover: bool = Field(default=False)
    failover_threshold_minutes: int = Field(default=5)

class NetworkPolicyConfig(BaseModel):
    """네트워크 정책 구성"""
    default_deny_all: bool = Field(default=True)
    allowed_connections: List[Dict[str, any]] = Field(default_factory=list)
    
    # 예시 구조
    # {
    #   "from_namespace": "aegis-production",
    #   "from_service": "user-service",
    #   "to_namespace": "aegis-data",
    #   "to_service": "postgresql",
    #   "port": 5432,
    #   "protocol": "TCP"
    # }

class InfrastructureState(BaseModel):
    """인프라 상태 추적"""
    cluster_id: str
    created_at: datetime
    last_updated: datetime
    status: str  # "provisioning", "ready", "updating", "error"
    
    # 리소스 현황
    total_nodes: int
    ready_nodes: int
    total_pods: int
    running_pods: int
    
    # 용량 정보
    total_cpu: str
    allocated_cpu: str
    total_memory: str
    allocated_memory: str
    total_storage: str
    used_storage: str
```

## 6. Error Handling

### 6.1. 인프라 에러 처리 전략

- **자동 복구**: Kubernetes의 기본 복구 기능(Pod 재시작)과 Liveness/Readiness Probe를 활용하여 대부분의 애플리케이션 오류를 자동으로 복구합니다.
- **알림 및 에스컬레이션**: 복구 불가능한 장애(예: 노드 다운, 스토리지 오류)는 Prometheus Alertmanager를 통해 즉시 담당자에게 알림(Slack, PagerDuty)을 보냅니다.
- **재시도 로직**: `shared-library`와 Istio 서비스 메시를 통해 외부 서비스 호출 실패 시 자동으로 재시도합니다.

## 7. Production Considerations

### 7.1. 확장성 (Scalability)
- **HPA (Horizontal Pod Autoscaler)**: CPU/메모리 사용량 및 커스텀 메트릭(예: 초당 요청 수)에 기반하여 애플리케이션 Pod를 3개에서 20개까지 자동으로 확장/축소합니다.
- **Cluster Autoscaler**: Pod를 스케줄링할 리소스가 부족할 경우, 클라우드 제공자와 연동하여 자동으로 Worker Node를 추가합니다.

### 7.2. 장애 복구 (Fault Tolerance)
- **다중 AZ 배포**: 모든 핵심 컴포넌트(Control Plane, Worker Node, 데이터베이스)를 3개의 가용 영역(AZ)에 분산 배포하여 단일 AZ 장애에 대응합니다.
- **Circuit Breaker**: Istio를 사용하여 특정 서비스에 장애가 발생했을 때, 장애가 다른 서비스로 전파되는 것을 차단합니다.

### 7.3. 캐싱 전략 (Caching Strategy)
- `shared-library`의 캐싱 데코레이터를 통해 다층 캐시(L1: In-memory, L2: Redis)를 구현합니다. 인프라는 고가용성이 보장된 Redis 클러스터를 제공합니다.

### 7.4. 모니터링 (Monitoring)
- Prometheus Operator를 사용하여 클러스터의 모든 메트릭을 수집하고, Grafana를 통해 시각화합니다. `user-service`의 로그인 성공률, `policy-service`의 이벤트 처리량 등 비즈니스 메트릭까지 포함됩니다.

### 7.5. 보안 (Security)
- **RBAC**: 개발자, 운영자, 서비스 계정별로 최소한의 권한만 부여합니다.
- **Network Policy**: 기본적으로 모든 Pod 간 통신을 차단하고, 명시적으로 필요한 통신만 허용합니다.
- **Secret 관리**: External Secrets Operator를 사용하여 AWS Secrets Manager, Vault 등과 연동, Kubernetes Secret을 안전하게 관리합니다.

## 8. Service Integration

### 8.1. 네트워크 정책 매트릭스

| From | To | Port | Protocol | 허용 여부 | Rationale |
|---|---|---|---|---|---|
| `aegis-production` (user-service) | `aegis-data` (PostgreSQL) | 5432 | TCP | ✅ | 사용자 정보 저장/조회 |
| `aegis-production` (policy-service) | `aegis-data` (Kafka) | 9092 | TCP | ✅ | 정책 변경 이벤트 발행/구독 |
| `Internet` | `aegis-production` | 443 | TCP | ❌ | Ingress를 통해서만 접근 허용 |

## 9. Integration Testing Strategy

### 9.1. 인프라 검증 (Infrastructure Validation)

#### 9.1.1. Terratest를 통한 인프라 검증

```go
// test/infrastructure_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/k8s"
    "github.com/stretchr/testify/assert"
)

func TestKubernetesCluster(t *testing.T) {
    t.Parallel()
    
    kubectlOptions := k8s.NewKubectlOptions("", "", "aegis-production")
    
    // 노드 수 검증
    nodes := k8s.GetNodes(t, kubectlOptions)
    assert.GreaterOrEqual(t, len(nodes), 3, "최소 3개의 워커 노드가 필요합니다")
    
    // Kubernetes 버전 검증
    version := k8s.GetKubernetesVersion(t, kubectlOptions)
    assert.Contains(t, version, "1.28", "Kubernetes 버전은 1.28.x여야 합니다")
    
    // 필수 네임스페이스 존재 확인
    requiredNamespaces := []string{
        "aegis-production",
        "aegis-data",
        "monitoring",
        "logging",
        "argocd",
    }
    
    for _, ns := range requiredNamespaces {
        k8s.GetNamespace(t, kubectlOptions, ns)
    }
}

func TestDatabaseOperators(t *testing.T) {
    t.Parallel()
    
    kubectlOptions := k8s.NewKubectlOptions("", "", "aegis-data")
    
    // PostgreSQL 클러스터 검증
    pgCluster := k8s.GetCustomResource(t, kubectlOptions, "postgresql.cnpg.io/v1", "Cluster", "aegis-postgresql")
    assert.NotNil(t, pgCluster)
    
    // Redis 클러스터 검증
    redisCluster := k8s.GetCustomResource(t, kubectlOptions, "redis.redis.opstreelabs.in/v1beta1", "RedisCluster", "aegis-redis")
    assert.NotNil(t, redisCluster)
    
    // Kafka 클러스터 검증
    kafkaCluster := k8s.GetCustomResource(t, kubectlOptions, "kafka.strimzi.io/v1beta2", "Kafka", "aegis-kafka")
    assert.NotNil(t, kafkaCluster)
}
```

#### 9.1.2. Smoke Tests

```bash
#!/bin/bash
# test/smoke_test.sh

set -e

echo "=== Aegis Infrastructure Smoke Tests ==="

# 1. 클러스터 접근성 테스트
echo "1. 클러스터 접근성 확인..."
kubectl cluster-info

# 2. 모든 노드가 Ready 상태인지 확인
echo "2. 노드 상태 확인..."
NOT_READY=$(kubectl get nodes --no-headers | grep -v " Ready" | wc -l)
if [ "$NOT_READY" -gt 0 ]; then
    echo "ERROR: $NOT_READY 개의 노드가 Ready 상태가 아닙니다"
    exit 1
fi

# 3. 핵심 시스템 Pod 상태 확인
echo "3. 시스템 Pod 상태 확인..."
NAMESPACES=("kube-system" "monitoring" "logging" "aegis-data" "argocd")
for ns in "${NAMESPACES[@]}"; do
    echo "  - $ns 네임스페이스 확인..."
    NOT_RUNNING=$(kubectl get pods -n $ns --no-headers | grep -v "Running\|Completed" | wc -l)
    if [ "$NOT_RUNNING" -gt 0 ]; then
        echo "WARNING: $ns에 $NOT_RUNNING 개의 Pod가 Running 상태가 아닙니다"
        kubectl get pods -n $ns | grep -v "Running\|Completed"
    fi
done

# 4. 데이터베이스 연결 테스트
echo "4. 데이터베이스 연결 테스트..."
kubectl run -n aegis-data pg-test --rm -i --restart=Never --image=postgres:15 -- \
    psql postgresql://aegis_user:password@postgresql.aegis-data.svc.cluster.local:5432/aegis -c "SELECT 1"

# 5. Redis 연결 테스트
echo "5. Redis 연결 테스트..."
kubectl run -n aegis-data redis-test --rm -i --restart=Never --image=redis:7 -- \
    redis-cli -h aegis-redis.aegis-data.svc.cluster.local PING

# 6. Kafka 연결 테스트
echo "6. Kafka 연결 테스트..."
kubectl run -n aegis-data kafka-test --rm -i --restart=Never --image=confluentinc/cp-kafka:7.5.0 -- \
    kafka-broker-api-versions --bootstrap-server aegis-kafka-bootstrap:9092

# 7. Prometheus 메트릭 수집 확인
echo "7. Prometheus 메트릭 수집 확인..."
PROM_POD=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n monitoring $PROM_POD -- wget -qO- http://localhost:9090/api/v1/targets | grep -q "\"health\":\"up\""

# 8. Grafana 접근성 확인
echo "8. Grafana 접근성 확인..."
GRAFANA_POD=$(kubectl get pods -n monitoring -l app=grafana -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n monitoring $GRAFANA_POD -- wget -qO- http://localhost:3000/api/health | grep -q "\"database\":\"ok\""

echo "=== 모든 Smoke Tests 통과 ==="
```

### 9.2. 카오스 엔지니어링 (Chaos Engineering)

#### 9.2.1. Chaos Mesh 실험 정의

```yaml
# chaos-experiments/pod-failure.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: user-service-pod-kill
  namespace: chaos-testing
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - aegis-production
    labelSelectors:
      app: user-service
  scheduler:
    cron: "@every 30m"
  duration: "10s"
---
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
  namespace: chaos-testing
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - aegis-production
    labelSelectors:
      app: policy-service
  delay:
    latency: "100ms"
    correlation: "100"
    jitter: "10ms"
  duration: "5m"
  scheduler:
    cron: "@every 2h"
---
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: memory-stress
  namespace: chaos-testing
spec:
  mode: one
  selector:
    namespaces:
      - aegis-production
    labelSelectors:
      app: recommendation-service
  stressors:
    memory:
      workers: 4
      size: "256MB"
  duration: "3m"
```

#### 9.2.2. 복구 검증 스크립트

```python
# test/chaos_validation.py
import time
import requests
from kubernetes import client, config

def test_auto_recovery():
    """Pod 종료 후 자동 복구 검증"""
    config.load_kube_config()
    v1 = client.CoreV1Api()
    
    # 초기 Pod 수 확인
    pods = v1.list_namespaced_pod(
        namespace="aegis-production",
        label_selector="app=user-service"
    )
    initial_count = len(pods.items)
    
    # Pod 하나 삭제
    v1.delete_namespaced_pod(
        name=pods.items[0].metadata.name,
        namespace="aegis-production"
    )
    
    # 30초 대기 후 복구 확인
    time.sleep(30)
    
    pods = v1.list_namespaced_pod(
        namespace="aegis-production",
        label_selector="app=user-service"
    )
    
    assert len(pods.items) == initial_count, "Pod가 자동으로 복구되지 않았습니다"
    
    # 모든 Pod가 Running 상태인지 확인
    for pod in pods.items:
        assert pod.status.phase == "Running", f"Pod {pod.metadata.name}이 Running 상태가 아닙니다"

def test_service_availability_during_chaos():
    """카오스 실험 중 서비스 가용성 검증"""
    api_endpoint = "https://api.aegis.example.com/health"
    
    success_count = 0
    total_requests = 100
    
    for _ in range(total_requests):
        try:
            response = requests.get(api_endpoint, timeout=5)
            if response.status_code == 200:
                success_count += 1
        except:
            pass
        time.sleep(0.1)
    
    availability = (success_count / total_requests) * 100
    assert availability >= 99.0, f"가용성이 99% 미만입니다: {availability}%"
```

### 9.3. 부하 테스트 (Load Testing)

#### 9.3.1. k6 부하 테스트 스크립트

```javascript
// test/load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // 워밍업
    { duration: '5m', target: 100 },  // 정상 부하
    { duration: '2m', target: 200 },  // 피크 부하
    { duration: '5m', target: 200 },  // 피크 유지
    { duration: '2m', target: 0 },    // 쿨다운
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.05'],
  },
};

const BASE_URL = 'https://api.aegis.example.com';

export default function () {
  // 1. 로그인 테스트
  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    email: 'test@example.com',
    password: 'password123',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(loginRes, {
    'login status is 200': (r) => r.status === 200,
    'login response time < 500ms': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);
  
  const token = loginRes.json('access_token');
  
  // 2. 정책 목록 조회
  const policiesRes = http.get(`${BASE_URL}/api/v1/policies`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  
  check(policiesRes, {
    'policies status is 200': (r) => r.status === 200,
    'policies response time < 300ms': (r) => r.timings.duration < 300,
  }) || errorRate.add(1);
  
  // 3. 추천 조회
  const recommendationsRes = http.get(`${BASE_URL}/api/v1/recommendations`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  
  check(recommendationsRes, {
    'recommendations status is 200': (r) => r.status === 200,
    'recommendations response time < 1000ms': (r) => r.timings.duration < 1000,
  }) || errorRate.add(1);
  
  sleep(1);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}
```

#### 9.3.2. 데이터베이스 부하 테스트

```python
# test/db_load_test.py
import asyncio
import asyncpg
import time
from concurrent.futures import ThreadPoolExecutor

async def run_query(pool, query):
    async with pool.acquire() as conn:
        return await conn.fetch(query)

async def database_load_test():
    """PostgreSQL 부하 테스트"""
    pool = await asyncpg.create_pool(
        host='postgresql.aegis-data.svc.cluster.local',
        port=5432,
        user='aegis_user',
        password='password',
        database='aegis',
        min_size=10,
        max_size=50
    )
    
    queries = [
        "SELECT * FROM users WHERE email = 'test@example.com'",
        "SELECT * FROM policies WHERE status = 'active' LIMIT 100",
        "SELECT COUNT(*) FROM events WHERE created_at > NOW() - INTERVAL '1 hour'",
    ]
    
    start_time = time.time()
    tasks = []
    
    # 1000개의 동시 쿼리 실행
    for _ in range(1000):
        for query in queries:
            tasks.append(run_query(pool, query))
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"총 {len(tasks)}개 쿼리 실행")
    print(f"소요 시간: {duration:.2f}초")
    print(f"QPS: {len(tasks) / duration:.2f}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(database_load_test())
```

### 9.4. 보안 테스트

#### 9.4.1. 취약점 스캔

```yaml
# security-scan-job.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: trivy-scan
  namespace: security
spec:
  schedule: "0 2 * * *"  # 매일 02:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: trivy
            image: aquasec/trivy:latest
            command:
            - trivy
            - image
            - --severity
            - HIGH,CRITICAL
            - --exit-code
            - "1"
            - --no-progress
            - user-service:latest
          restartPolicy: OnFailure
```

#### 9.4.2. 네트워크 정책 검증

```bash
#!/bin/bash
# test/network_policy_test.sh

echo "=== 네트워크 정책 검증 ==="

# 1. 허용된 통신 테스트
echo "1. user-service -> PostgreSQL 통신 (허용되어야 함)"
kubectl run -n aegis-production test-allowed --rm -i --restart=Never --image=postgres:15 -- \
    psql postgresql://aegis_user:password@postgresql.aegis-data.svc.cluster.local:5432/aegis -c "SELECT 1"

if [ $? -eq 0 ]; then
    echo "✓ 허용된 통신 성공"
else
    echo "✗ 허용된 통신 실패"
    exit 1
fi

# 2. 차단된 통신 테스트
echo "2. 외부 -> PostgreSQL 직접 통신 (차단되어야 함)"
kubectl run -n default test-blocked --rm -i --restart=Never --image=postgres:15 --timeout=10s -- \
    psql postgresql://aegis_user:password@postgresql.aegis-data.svc.cluster.local:5432/aegis -c "SELECT 1"

if [ $? -ne 0 ]; then
    echo "✓ 차단된 통신 정상 차단됨"
else
    echo "✗ 차단되어야 할 통신이 허용됨"
    exit 1
fi

echo "=== 네트워크 정책 검증 완료 ==="
```

## 10. Performance Benchmarks

| 항목 | 목표 지표 | 측정 방법 |
|---|---|---|
| 클러스터 준비 시간 | < 15분 | Terraform apply 완료 시간 |
| 애플리케이션 배포 시간 | < 5분 | ArgoCD 동기화 완료 시간 |
| Pod 시작 시간 | < 30초 | `kube-state-metrics` |
| API Gateway 응답 시간 (p99) | < 50ms | Prometheus (Istio 메트릭) |

## 11. Monitoring

### 11.1. SLI/SLO 정의

| SLI | SLO | 설명 |
|---|---|---|
| API 가용성 | 99.9% | 5xx 에러를 제외한 성공 응답 비율 |
| API 응답 시간 (p95) | < 500ms | 95%의 요청이 500ms 이내에 처리 |

## 12. API Specification

인프라 자체는 API를 제공하지 않으나, Kubernetes API와 각 클라우드 제공자의 API를 사용하여 관리 및 자동화를 수행합니다.

## 13. Database Schema

인프라는 데이터베이스 스키마를 직접 소유하지 않고, `shared-library`의 `SchemaRegistry`를 통해 스키마 변경을 지원합니다.

## 14. Configuration Management

- **도구**: Kustomize, Helm
- **방법**: 기본(base) 매니페스트를 정의하고, 환경별(dev/staging/prod)로 Kustomize 오버레이를 사용하여 설정을 변경합니다.

## 15. Logging Strategy

- **수집**: Filebeat가 모든 노드의 컨테이너 로그를 수집합니다.
- **처리**: Logstash가 로그를 파싱하고, 민감 정보를 마스킹합니다.
- **저장**: Elasticsearch에 저장하며, ILM 정책에 따라 30일 후 자동 삭제합니다.

## 16. Observability

- **분산 추적**: Istio와 OpenTelemetry를 연동하여 모든 요청에 Trace ID를 자동으로 주입하고, Jaeger로 시각화합니다.

## 17. Disaster Recovery

### 17.1. 복구 목표
- **RTO (Recovery Time Objective)**: 2시간
- **RPO (Recovery Point Objective)**: 15분

### 17.2. 복구 절차
1. **장애 감지**: Alertmanager가 장애 감지 후 PagerDuty로 담당자 호출.
2. **클러스터 복구**: Velero를 사용하여 백업에서 Kubernetes 리소스 복원.
3. **데이터베이스 복구**: 백업에서 데이터베이스 복원 및 WAL 로그 적용.
4. **서비스 검증**: Smoke Test를 통해 서비스 정상 동작 확인.

## 18. Compliance and Audit

- **도구**: OPA (Open Policy Agent) Gatekeeper
- **정책**: `latest` 태그 이미지 배포 금지, non-root 유저 실행 강제 등.
- **감사**: Kubernetes Audit Log를 활성화하여 모든 API 서버 요청을 기록합니다.

## 19. Dependency Management

- **Kubernetes 버전**: `1.28.x`
- **Istio 버전**: `1.20.x`
- **Helm 차트**: 버전은 `Chart.yaml`에 명시하고 관리합니다.

## 20. Development Workflow

인프라 변경은 GitOps 워크플로우를 따릅니다.
1. **PR 생성**: Terraform 또는 Helm 차트 수정 후 `main` 브랜치로 Pull Request를 생성합니다.
2. **자동 검증**: CI 파이프라인에서 `terraform plan`, `helm lint`를 실행하여 유효성을 검증합니다.
3. **배포**: PR이 머지되면 ArgoCD가 자동으로 변경사항을 클러스터에 동기화합니다.

## 21. Capacity Planning

- 분기별로 리소스 사용률과 비용을 검토하고, VPA의 권장사항을 참고하여 리소스 요청/제한을 재조정합니다.

## 22. Documentation

- **IaC 저장소**: `README.md`에 각 모듈의 사용법과 변수를 상세히 기술합니다.
- **ADR**: 주요 설계 결정을 `docs/adr` 디렉토리에 기록합니다.

## 23. Internationalization
- 해당 없음

## 24. Accessibility
- 해당 없음

## 25. Versioning Strategy
- **IaC 코드**: Git 태그를 사용하여 SemVer로 버전을 관리합니다.

## 26. Cost Optimization
- **스팟 인스턴스**: 스테이징 환경 및 비프로덕션 워크로드에 스팟 인스턴스를 활용합니다.
- **리소스 최적화**: VPA를 사용하여 Pod의 리소스 요청을 최적화합니다.

## 27. Team Collaboration
- **코드 소유권**: `CODEOWNERS` 파일을 사용하여 각 인프라 구성 요소의 담당자를 지정합니다.
- **커뮤니케이션**: 인프라 관련 논의는 `#infra` Slack 채널에서 진행합니다.
