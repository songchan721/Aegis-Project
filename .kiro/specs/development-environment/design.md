# Development Environment Design Document

## Overview

이지스(Aegis) 개발 환경은 Docker Compose 기반의 컨테이너화된 로컬 개발 환경을 제공합니다. 모든 개발자가 동일한 환경에서 작업할 수 있도록 하며, 프로덕션 환경과 최대한 유사하게 구성됩니다.

## Shared Library Development

개발 환경에서 shared-library를 개발 모드로 사용:

```bash
# shared-library를 editable 모드로 설치
cd shared-library
pip install -e .

# 다른 서비스에서 자동으로 변경사항 반영됨
cd ../user-service
python -m app.main  # shared-library 변경사항 즉시 반영
```

**장점:**
- shared-library 수정 시 재설치 불필요
- 실시간 디버깅 가능
- 통합 개발 환경

## Architecture

### 전체 아키텍처 다이어그램

```mermaid
graph TB
    subgraph "Developer Machine"
        subgraph "IDE & Tools"
            VSCODE[VS Code]
            GIT[Git]
            DOCKER[Docker Desktop]
        end
        
        subgraph "Docker Compose Services"
            subgraph "Application Services"
                API[FastAPI Backend]
                WEB[React Frontend]
            end
            
            subgraph "Data Services"
                POSTGRES[(PostgreSQL)]
                REDIS[(Redis)]
                MILVUS[(Milvus)]
                NEO4J[(Neo4j)]
            end
            
            subgraph "Message Queue"
                KAFKA[Apache Kafka]
                ZOOKEEPER[Zookeeper]
            end
            
            subgraph "Development Tools"
                SWAGGER[Swagger UI]
                PGADMIN[pgAdmin]
                REDISINSIGHT[Redis Insight]
                NEO4JBROWSER[Neo4j Browser]
            end
        end
        
        subgraph "Local File System"
            CODE[Source Code]
            ENV[Environment Files]
            DATA[Local Data]
            LOGS[Log Files]
        end
    end
    
    VSCODE --> CODE
    API --> POSTGRES
    API --> REDIS
    API --> MILVUS
    API --> NEO4J
    API --> KAFKA
    WEB --> API
    KAFKA --> ZOOKEEPER
```

## Components and Interfaces

### 1. Docker Compose 구성

#### 1.1 메인 서비스 정의
```yaml
# docker-compose.yml
version: '3.8'

services:
  # Backend API Service
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://aegis:password@postgres:5432/aegis_dev
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    volumes:
      - ./backend:/app
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
      - kafka
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    
  # Frontend Web Service
  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm start
```

#### 1.2 데이터베이스 서비스
```yaml
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: aegis_dev
      POSTGRES_USER: aegis
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    
  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    
  # Milvus Vector Database
  milvus:
    image: milvusdb/milvus:v2.3.0
    ports:
      - "19530:19530"
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    depends_on:
      - etcd
      - minio
      
  # Neo4j Graph Database
  neo4j:
    image: neo4j:5.0-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
```

#### 1.3 메시지 큐 서비스
```yaml
  # Zookeeper for Kafka
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data
      
  # Apache Kafka
  kafka:
    image: confluentinc/cp-kafka:7.4.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    volumes:
      - kafka_data:/var/lib/kafka/data
    depends_on:
      - zookeeper
```

### 2. 개발 도구 통합

#### 2.1 VS Code 설정
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/node_modules": true
  }
}
```

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.pylint",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode-remote.remote-containers"
  ]
}
```

#### 2.2 디버깅 설정
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Debug",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/.venv/bin/uvicorn",
      "args": ["app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "DATABASE_URL": "postgresql://aegis:password@localhost:5432/aegis_dev",
        "REDIS_URL": "redis://localhost:6379/0"
      }
    },
    {
      "name": "React Debug",
      "type": "node",
      "request": "launch",
      "cwd": "${workspaceFolder}/frontend",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["start"]
    }
  ]
}
```

### 3. 환경 설정 관리

#### 3.1 환경 변수 구조
```bash
# .env.development
# Database Configuration
DATABASE_URL=postgresql://aegis:password@localhost:5432/aegis_dev
DATABASE_TEST_URL=postgresql://aegis:password@localhost:5432/aegis_test

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_TEST_URL=redis://localhost:6379/1

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=aegis_dev

# Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Graph Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# AI/ML Services
OPENAI_API_KEY=your_openai_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Application Settings
DEBUG=true
LOG_LEVEL=DEBUG
SECRET_KEY=dev_secret_key_change_in_production
```

#### 3.2 설정 로더
```python
# backend/app/core/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str
    database_test_url: Optional[str] = None
    
    # Redis
    redis_url: str
    redis_test_url: Optional[str] = None
    
    # Kafka
    kafka_bootstrap_servers: str
    kafka_topic_prefix: str = "aegis"
    
    # Vector Database
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    
    # Graph Database
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    # AI/ML
    openai_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Data Models

### 개발 환경 데이터 구조

#### 1. 데이터베이스 초기화 스크립트
```sql
-- database/init/01_create_databases.sql
CREATE DATABASE aegis_dev;
CREATE DATABASE aegis_test;

-- Create extensions
\c aegis_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

\c aegis_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
```

#### 2. 시드 데이터 구조
```python
# backend/app/db/seed_data.py
from typing import List, Dict, Any

SEED_USERS: List[Dict[str, Any]] = [
    {
        "email": "admin@aegis.dev",
        "password": "admin123!",
        "name": "관리자",
        "is_active": True,
        "is_admin": True
    },
    {
        "email": "user@aegis.dev", 
        "password": "user123!",
        "name": "테스트 사용자",
        "is_active": True,
        "is_admin": False
    }
]

SEED_POLICIES: List[Dict[str, Any]] = [
    {
        "title": "소상공인 운영자금 지원",
        "organization": "소상공인시장진흥공단",
        "content": "소상공인의 운영자금 지원을 위한 정책...",
        "target_business_type": ["소상공인"],
        "target_regions": ["전국"],
        "support_amount": "최대 2,000만원",
        "application_period": "2025-01-01 ~ 2025-12-31"
    }
]
```

## Error Handling

### 개발 환경 에러 처리 전략

#### 1. 서비스 헬스 체크
```python
# backend/app/api/health.py
from fastapi import APIRouter, HTTPException
from app.core.database import get_db_session
from app.core.redis import get_redis_client
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """개발 환경 서비스 상태 확인"""
    services = {}
    
    # PostgreSQL 체크
    try:
        async with get_db_session() as db:
            await db.execute("SELECT 1")
        services["postgresql"] = "healthy"
    except Exception as e:
        services["postgresql"] = f"unhealthy: {str(e)}"
    
    # Redis 체크
    try:
        redis = get_redis_client()
        await redis.ping()
        services["redis"] = "healthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"
    
    # 전체 상태 결정
    all_healthy = all(status == "healthy" for status in services.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": services,
        "environment": "development"
    }
```

#### 2. 개발용 에러 핸들러
```python
# backend/app/core/exceptions.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback
import logging

logger = logging.getLogger(__name__)

async def development_exception_handler(request: Request, exc: Exception):
    """개발 환경용 상세 에러 정보 제공"""
    
    error_detail = {
        "error": str(exc),
        "type": type(exc).__name__,
        "traceback": traceback.format_exc(),
        "request": {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
        }
    }
    
    logger.error(f"Development error: {error_detail}")
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )
```

## Testing Strategy

### 개발 환경 테스트 구성

#### 1. 테스트 데이터베이스 설정
```python
# backend/tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings
from app.db.base import Base

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 설정"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """테스트 데이터베이스 엔진"""
    engine = create_async_engine(settings.database_test_url)
    
    # 테스트 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 테스트 테이블 삭제
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_db(test_engine):
    """테스트 데이터베이스 세션"""
    async with AsyncSession(test_engine) as session:
        yield session
        await session.rollback()
```

#### 2. 통합 테스트 설정
```python
# backend/tests/test_integration.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_full_stack_health():
    """전체 스택 헬스 체크 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["environment"] == "development"
        assert "services" in data
```

---

이 설계 문서는 개발 환경의 모든 구성 요소와 설정을 상세히 정의합니다. 다음 단계로 tasks.md를 작성하여 실제 구현 작업을 정의하겠습니다.

## S
eed Data Generation Strategy

### 시드 데이터 구조

```python
# scripts/seed_data.py
from typing import List, Dict
from faker import Faker
import random
from datetime import datetime, timedelta
import asyncio
from aegis_shared.database import DatabaseManager
from aegis_shared.logging import get_logger

logger = get_logger(__name__)
fake = Faker('ko_KR')  # 한국어 데이터 생성

class SeedDataGenerator:
    """시드 데이터 생성기"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.generated_ids = {
            'users': [],
            'policies': [],
            'search_queries': [],
            'recommendations': []
        }
    
    async def generate_all(self):
        """모든 시드 데이터 생성"""
        logger.info("Starting seed data generation")
        
        await self.generate_users(count=10)
        await self.generate_policies(count=100)
        await self.generate_search_queries(count=50)
        await self.generate_recommendation_feedback(count=30)
        
        logger.info("Seed data generation completed")
    
    async def generate_users(self, count: int = 10):
        """테스트 사용자 생성"""
        logger.info(f"Generating {count} test users")
        
        users = []
        for i in range(count):
            user = {
                'user_id': fake.uuid4(),
                'email': fake.email(),
                'name': fake.name(),
                'phone': fake.phone_number(),
                'business_type': random.choice([
                    '제조업', '서비스업', '도소매업', 'IT/소프트웨어', '음식점업'
                ]),
                'business_stage': random.choice([
                    '예비창업', '창업 1년차', '창업 3년차', '창업 5년차'
                ]),
                'location': fake.city(),
                'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 365)),
                'is_active': True
            }
            users.append(user)
            self.generated_ids['users'].append(user['user_id'])
        
        async with self.db_manager.session() as session:
            # 실제 DB 삽입 로직
            pass
        
        logger.info(f"Generated {len(users)} users")
        return users
    
    async def generate_policies(self, count: int = 100):
        """샘플 정책 생성"""
        logger.info(f"Generating {count} sample policies")
        
        policy_templates = [
            {
                'category': '창업지원',
                'keywords': ['창업', '지원금', '보조금', '초기자금'],
                'target_audience': ['예비창업자', '초기창업자']
            },
            {
                'category': '기술개발',
                'keywords': ['R&D', '기술개발', '연구개발', '특허'],
                'target_audience': ['기술기업', '제조업']
            },
            {
                'category': '판로지원',
                'keywords': ['판로', '마케팅', '수출', '온라인판매'],
                'target_audience': ['소상공인', '중소기업']
            },
            {
                'category': '인력지원',
                'keywords': ['인력', '채용', '교육', '훈련'],
                'target_audience': ['전체']
            },
            {
                'category': '자금지원',
                'keywords': ['융자', '대출', '보증', '투자'],
                'target_audience': ['중소기업', '소상공인']
            }
        ]
        
        policies = []
        for i in range(count):
            template = random.choice(policy_templates)
            
            policy = {
                'policy_id': fake.uuid4(),
                'title': f"{template['category']} - {fake.catch_phrase()}",
                'description': fake.text(max_nb_chars=500),
                'category': template['category'],
                'keywords': random.sample(template['keywords'], k=random.randint(2, 4)),
                'target_audience': random.choice(template['target_audience']),
                'support_amount': random.choice([
                    '최대 1,000만원', '최대 3,000만원', '최대 5,000만원', 
                    '최대 1억원', '최대 3억원'
                ]),
                'application_period': {
                    'start': (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    'end': (datetime.utcnow() + timedelta(days=60)).isoformat()
                },
                'organization': random.choice([
                    '중소벤처기업부', '고용노동부', '산업통상자원부', 
                    '서울시', '경기도', '부산시'
                ]),
                'url': fake.url(),
                'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 180)),
                'is_active': True
            }
            policies.append(policy)
            self.generated_ids['policies'].append(policy['policy_id'])
        
        async with self.db_manager.session() as session:
            # 실제 DB 삽입 로직
            pass
        
        logger.info(f"Generated {len(policies)} policies")
        return policies
    
    async def generate_search_queries(self, count: int = 50):
        """검색 쿼리 생성"""
        logger.info(f"Generating {count} search queries")
        
        query_templates = [
            "창업 지원금",
            "소상공인 대출",
            "기술개발 R&D 지원",
            "청년 창업 지원",
            "여성 창업 지원",
            "제조업 지원 정책",
            "온라인 판매 지원",
            "수출 지원 프로그램",
            "특허 출원 지원",
            "직원 채용 지원금"
        ]
        
        queries = []
        for i in range(count):
            user_id = random.choice(self.generated_ids['users']) if self.generated_ids['users'] else None
            
            query = {
                'query_id': fake.uuid4(),
                'user_id': user_id,
                'query_text': random.choice(query_templates),
                'filters': {
                    'category': random.choice(['창업지원', '기술개발', '판로지원', None]),
                    'location': random.choice(['서울', '경기', '부산', None])
                },
                'results_count': random.randint(5, 50),
                'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 90))
            }
            queries.append(query)
            self.generated_ids['search_queries'].append(query['query_id'])
        
        async with self.db_manager.session() as session:
            # 실제 DB 삽입 로직
            pass
        
        logger.info(f"Generated {len(queries)} search queries")
        return queries
    
    async def generate_recommendation_feedback(self, count: int = 30):
        """추천 피드백 생성"""
        logger.info(f"Generating {count} recommendation feedbacks")
        
        feedbacks = []
        for i in range(count):
            user_id = random.choice(self.generated_ids['users']) if self.generated_ids['users'] else None
            policy_id = random.choice(self.generated_ids['policies']) if self.generated_ids['policies'] else None
            
            feedback = {
                'feedback_id': fake.uuid4(),
                'user_id': user_id,
                'policy_id': policy_id,
                'action': random.choice(['view', 'click', 'bookmark', 'apply']),
                'rating': random.randint(1, 5) if random.random() > 0.5 else None,
                'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 60))
            }
            feedbacks.append(feedback)
        
        async with self.db_manager.session() as session:
            # 실제 DB 삽입 로직
            pass
        
        logger.info(f"Generated {len(feedbacks)} feedbacks")
        return feedbacks
    
    async def reset_database(self):
        """데이터베이스 초기화"""
        logger.warning("Resetting database - all data will be deleted")
        
        async with self.db_manager.session() as session:
            # 모든 테이블 데이터 삭제 (역순)
            await session.execute("TRUNCATE TABLE recommendation_feedback CASCADE")
            await session.execute("TRUNCATE TABLE search_queries CASCADE")
            await session.execute("TRUNCATE TABLE policies CASCADE")
            await session.execute("TRUNCATE TABLE users CASCADE")
        
        logger.info("Database reset completed")

# CLI 인터페이스
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed data generator for Aegis')
    parser.add_argument('--reset', action='store_true', help='Reset database before seeding')
    parser.add_argument('--users', type=int, default=10, help='Number of users to generate')
    parser.add_argument('--policies', type=int, default=100, help='Number of policies to generate')
    parser.add_argument('--queries', type=int, default=50, help='Number of search queries to generate')
    parser.add_argument('--feedbacks', type=int, default=30, help='Number of feedbacks to generate')
    
    args = parser.parse_args()
    
    # 데이터베이스 연결
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://aegis:aegis@localhost:5432/aegis_dev"
    )
    
    generator = SeedDataGenerator(db_manager)
    
    if args.reset:
        await generator.reset_database()
    
    await generator.generate_users(count=args.users)
    await generator.generate_policies(count=args.policies)
    await generator.generate_search_queries(count=args.queries)
    await generator.generate_recommendation_feedback(count=args.feedbacks)
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 시드 데이터 사용법

```bash
# 기본 시드 데이터 생성
python scripts/seed_data.py

# 데이터베이스 리셋 후 생성
python scripts/seed_data.py --reset

# 커스텀 개수 지정
python scripts/seed_data.py --users 20 --policies 200 --queries 100

# Docker Compose에서 자동 실행
docker-compose up -d
docker-compose exec api python scripts/seed_data.py --reset
```

### 프로덕션 유사 데이터 생성

```python
# scripts/generate_production_like_data.py
class ProductionLikeDataGenerator(SeedDataGenerator):
    """프로덕션 유사 데이터 생성기"""
    
    async def generate_realistic_user_behavior(self):
        """실제 사용자 행동 패턴 시뮬레이션"""
        # 1. 사용자 생성
        users = await self.generate_users(count=100)
        
        # 2. 각 사용자별 검색 패턴 생성
        for user in users:
            # 활성 사용자: 주 2-3회 검색
            if random.random() > 0.3:
                search_count = random.randint(2, 5)
                for _ in range(search_count):
                    await self.generate_user_search(user['user_id'])
        
        # 3. 추천 클릭 및 피드백 생성
        for user in users:
            if random.random() > 0.5:
                await self.generate_user_interactions(user['user_id'])
    
    async def generate_time_series_data(self, days: int = 90):
        """시계열 데이터 생성"""
        for day in range(days):
            date = datetime.utcnow() - timedelta(days=days - day)
            
            # 요일별 트래픽 패턴
            if date.weekday() < 5:  # 평일
                daily_users = random.randint(50, 100)
            else:  # 주말
                daily_users = random.randint(20, 40)
            
            # 해당 날짜의 데이터 생성
            await self.generate_daily_data(date, daily_users)
```

### 데이터 검증

```python
# scripts/validate_seed_data.py
class SeedDataValidator:
    """시드 데이터 검증"""
    
    async def validate_all(self):
        """모든 데이터 검증"""
        checks = [
            self.check_user_count(),
            self.check_policy_count(),
            self.check_referential_integrity(),
            self.check_data_quality()
        ]
        
        results = await asyncio.gather(*checks)
        
        for check_name, passed, message in results:
            if passed:
                logger.info(f"✓ {check_name}: {message}")
            else:
                logger.error(f"✗ {check_name}: {message}")
    
    async def check_referential_integrity(self):
        """참조 무결성 확인"""
        # 모든 search_queries의 user_id가 users 테이블에 존재하는지 확인
        # 모든 recommendation_feedback의 policy_id가 policies 테이블에 존재하는지 확인
        pass
```

---

이 시드 데이터 생성 전략은 개발과 테스트에 필요한 실제와 유사한 데이터를 효율적으로 생성합니다.


## Service Integration

### Docker Compose 네트워크 구성

```yaml
# docker-compose.yml
networks:
  aegis-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

services:
  api:
    networks:
      aegis-network:
        ipv4_address: 172.28.0.10
  
  postgres:
    networks:
      aegis-network:
        ipv4_address: 172.28.0.20
  
  redis:
    networks:
      aegis-network:
        ipv4_address: 172.28.0.30
```

### 서비스 간 통신

| Source Service | Target Service | Protocol | Port | Purpose |
|---------------|----------------|----------|------|---------|
| api | postgres | TCP | 5432 | 데이터베이스 연결 |
| api | redis | TCP | 6379 | 캐시 연결 |
| api | kafka | TCP | 9092 | 이벤트 발행/구독 |
| api | milvus | gRPC | 19530 | 벡터 검색 |
| api | neo4j | Bolt | 7687 | 그래프 쿼리 |
| web | api | HTTP | 8000 | API 호출 |
| kafka | zookeeper | TCP | 2181 | 클러스터 관리 |

### 서비스 디스커버리

```python
# backend/app/core/service_discovery.py
from typing import Dict
import os

class ServiceDiscovery:
    """개발 환경 서비스 디스커버리"""
    
    @staticmethod
    def get_service_url(service_name: str) -> str:
        """서비스 URL 반환"""
        service_urls = {
            'postgres': os.getenv('DATABASE_URL', 'postgresql://aegis:password@postgres:5432/aegis_dev'),
            'redis': os.getenv('REDIS_URL', 'redis://redis:6379/0'),
            'kafka': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'milvus': f"{os.getenv('MILVUS_HOST', 'milvus')}:{os.getenv('MILVUS_PORT', '19530')}",
            'neo4j': os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        }
        return service_urls.get(service_name, '')
    
    @staticmethod
    def check_service_health(service_name: str) -> bool:
        """서비스 헬스 체크"""
        # 각 서비스별 헬스 체크 로직
        pass
```

## Monitoring

### Prometheus 메트릭 수집

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - aegis-network
```

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aegis-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 개발 환경 메트릭

```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import make_asgi_app

# 요청 카운터
request_count = Counter(
    'aegis_dev_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

# 응답 시간
request_duration = Histogram(
    'aegis_dev_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

# 활성 연결
active_connections = Gauge(
    'aegis_dev_active_connections',
    'Active database connections'
)

# FastAPI 통합
metrics_app = make_asgi_app()
```

### 로그 수집

```yaml
# docker-compose.yml
services:
  filebeat:
    image: docker.elastic.io/beats/filebeat:8.8.0
    volumes:
      - ./logs:/logs:ro
      - ./monitoring/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
    networks:
      - aegis-network
    depends_on:
      - elasticsearch
```

## API Specification

### OpenAPI 스펙 파일

```yaml
# api/openapi.yaml
openapi: 3.0.0
info:
  title: Aegis Development API
  version: 1.0.0
  description: 이지스 개발 환경 API 명세

servers:
  - url: http://localhost:8000
    description: 로컬 개발 서버

paths:
  /health:
    get:
      summary: 헬스 체크
      responses:
        '200':
          description: 서비스 정상
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'
  
  /api/v1/users:
    get:
      summary: 사용자 목록 조회
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
      responses:
        '200':
          description: 성공
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'

components:
  schemas:
    HealthResponse:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, unhealthy]
        services:
          type: object
          additionalProperties:
            type: string
    
    User:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        name:
          type: string
        created_at:
          type: string
          format: date-time
```

### API 계약 테스트

```python
# tests/contract/test_api_contract.py
import pytest
from pact import Consumer, Provider

pact = Consumer('frontend').has_pact_with(Provider('api'))

def test_get_users_contract():
    """사용자 목록 조회 계약 테스트"""
    expected = {
        'user_id': '123e4567-e89b-12d3-a456-426614174000',
        'email': 'test@example.com',
        'name': '테스트 사용자'
    }
    
    (pact
     .given('사용자가 존재함')
     .upon_receiving('사용자 목록 요청')
     .with_request('get', '/api/v1/users')
     .will_respond_with(200, body=[expected]))
    
    with pact:
        # 실제 API 호출 테스트
        pass
```

## Database Schema

### 전체 ERD

```mermaid
erDiagram
    USERS ||--o{ SEARCH_QUERIES : creates
    USERS ||--o{ RECOMMENDATION_FEEDBACK : provides
    POLICIES ||--o{ RECOMMENDATION_FEEDBACK : receives
    POLICIES ||--o{ POLICY_KEYWORDS : has
    
    USERS {
        uuid user_id PK
        string email UK
        string name
        string phone
        string business_type
        string business_stage
        string location
        timestamp created_at
        boolean is_active
    }
    
    POLICIES {
        uuid policy_id PK
        string title
        text description
        string category
        jsonb keywords
        string target_audience
        string support_amount
        jsonb application_period
        string organization
        string url
        timestamp created_at
        boolean is_active
    }
    
    SEARCH_QUERIES {
        uuid query_id PK
        uuid user_id FK
        string query_text
        jsonb filters
        integer results_count
        timestamp created_at
    }
    
    RECOMMENDATION_FEEDBACK {
        uuid feedback_id PK
        uuid user_id FK
        uuid policy_id FK
        string action
        integer rating
        timestamp created_at
    }
    
    POLICY_KEYWORDS {
        uuid keyword_id PK
        uuid policy_id FK
        string keyword
        float weight
    }
```

### 마이그레이션 전략

```python
# database/migrations/env.py
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db.base import Base

def run_migrations_online():
    """온라인 마이그레이션 실행"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            compare_type=True,
            compare_server_default=True
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

```bash
# 마이그레이션 명령어
# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add users table"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1

# 마이그레이션 히스토리
alembic history
```

## Logging Strategy

### 로그 레벨 정책

| 환경 | DEBUG | INFO | WARNING | ERROR |
|------|-------|------|---------|-------|
| Development | ✅ | ✅ | ✅ | ✅ |
| Test | ❌ | ✅ | ✅ | ✅ |

### 로그 포맷

```python
# backend/app/core/logging_config.py
import structlog
from pythonjsonlogger import jsonlogger

def configure_logging():
    """구조화된 로깅 설정"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# 로그 예시
logger = structlog.get_logger()
logger.info(
    "user_login",
    user_id="123",
    email="user@example.com",
    ip_address="127.0.0.1"
)
```

### 로그 출력 예시

```json
{
  "timestamp": "2025-10-07T10:30:45.123456Z",
  "level": "info",
  "logger": "app.api.users",
  "event": "user_login",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "ip_address": "127.0.0.1",
  "request_id": "req_abc123",
  "duration_ms": 45.2
}
```

### 로그 수집 및 저장

```yaml
# monitoring/filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /logs/api/*.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      service: aegis-api
      environment: development

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "aegis-dev-logs-%{+yyyy.MM.dd}"
```

### 민감 정보 마스킹

```python
# backend/app/core/log_masking.py
import re

class LogMasker:
    """로그 민감 정보 마스킹"""
    
    PATTERNS = {
        'email': r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'phone': r'(\d{3})-(\d{3,4})-(\d{4})',
        'password': r'(password["\']?\s*[:=]\s*["\']?)([^"\']+)',
        'token': r'(token["\']?\s*[:=]\s*["\']?)([^"\']+)',
    }
    
    @classmethod
    def mask(cls, text: str) -> str:
        """민감 정보 마스킹"""
        masked = text
        
        # 이메일 마스킹: user@example.com -> u***@example.com
        masked = re.sub(
            cls.PATTERNS['email'],
            lambda m: f"{m.group(1)[0]}***@{m.group(2)}",
            masked
        )
        
        # 전화번호 마스킹: 010-1234-5678 -> 010-****-5678
        masked = re.sub(
            cls.PATTERNS['phone'],
            lambda m: f"{m.group(1)}-****-{m.group(3)}",
            masked
        )
        
        # 비밀번호/토큰 마스킹
        masked = re.sub(cls.PATTERNS['password'], r'\1***MASKED***', masked)
        masked = re.sub(cls.PATTERNS['token'], r'\1***MASKED***', masked)
        
        return masked
```

---

이 개발 환경 설계 문서는 로컬 개발에 필요한 모든 구성 요소와 설정을 상세히 정의하며, 프로덕션 환경과 유사한 경험을 제공합니다.
