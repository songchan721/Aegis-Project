# Private PyPI 설정 가이드

Aegis Shared Library를 Private PyPI 서버에 배포하고 관리하는 방법을 설명합니다.

## 1. Private PyPI 서버 옵션

### 1.1 PyPI Simple (권장)

가장 간단한 방법으로 파일 시스템 기반의 Private PyPI 서버입니다.

```bash
# pypi-server 설치
pip install pypiserver

# 패키지 디렉토리 생성
mkdir -p /var/pypi/packages

# 서버 시작
pypi-server -p 8080 -P . -a . /var/pypi/packages
```

### 1.2 DevPI

더 고급 기능을 제공하는 Private PyPI 서버입니다.

```bash
# devpi 설치
pip install devpi-server devpi-web

# 서버 초기화
devpi-init

# 서버 시작
devpi-server --start --init
```

### 1.3 JFrog Artifactory

엔터프라이즈급 아티팩트 관리 솔루션입니다.

```bash
# Docker로 Artifactory 실행
docker run --name artifactory -d -p 8081:8081 -p 8082:8082 \
  docker.bintray.io/jfrog/artifactory-oss:latest
```

### 1.4 Nexus Repository

Sonatype의 리포지토리 관리자입니다.

```bash
# Docker로 Nexus 실행
docker run -d -p 8081:8081 --name nexus sonatype/nexus3
```

## 2. Poetry 설정

### 2.1 Private Repository 추가

```bash
# Private PyPI 서버 추가
poetry config repositories.private-pypi http://your-pypi-server:8080/simple/

# 인증 정보 설정
poetry config http-basic.private-pypi username password
```

### 2.2 pyproject.toml 설정

```toml
# pyproject.toml
[tool.poetry]
name = "aegis-shared"
version = "0.1.0"
# ... 기타 설정

# Private repository 설정
[[tool.poetry.source]]
name = "private-pypi"
url = "http://your-pypi-server:8080/simple/"
priority = "supplemental"

# 패키지별 소스 지정
[tool.poetry.dependencies]
python = "^3.11"
# 공개 패키지들...

# Private 패키지 (필요한 경우)
# some-private-package = {version = "^1.0.0", source = "private-pypi"}
```

### 2.3 배포 설정

```bash
# Private PyPI에 배포
poetry publish --repository private-pypi

# 토큰 기반 인증 (권장)
poetry config pypi-token.private-pypi your-api-token
```

## 3. Docker 기반 Private PyPI 설정

### 3.1 Docker Compose 설정

```yaml
# docker-compose.pypi.yml
version: '3.8'

services:
  pypi-server:
    image: pypiserver/pypiserver:latest
    container_name: aegis-pypi-server
    ports:
      - "8080:8080"
    volumes:
      - ./pypi-packages:/data/packages
      - ./pypi-auth:/data/auth
    environment:
      - PYPI_PASSWORDS=/data/auth/.htpasswd
    command: >
      -p 8080
      -P /data/auth/.htpasswd
      -a update,download,list
      /data/packages
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: aegis-pypi-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - pypi-server
    restart: unless-stopped
```

### 3.2 Nginx 설정

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream pypi {
        server pypi-server:8080;
    }

    server {
        listen 80;
        server_name pypi.aegis.local;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name pypi.aegis.local;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        client_max_body_size 100M;

        location / {
            proxy_pass http://pypi;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 3.3 인증 설정

```bash
# htpasswd 파일 생성
mkdir -p pypi-auth
htpasswd -c pypi-auth/.htpasswd aegis-user

# 패키지 디렉토리 생성
mkdir -p pypi-packages

# 서버 시작
docker-compose -f docker-compose.pypi.yml up -d
```

## 4. 자동화 스크립트

### 4.1 배포 스크립트

```python
# scripts/deploy.py
#!/usr/bin/env python3
"""
Private PyPI 배포 스크립트
"""

import subprocess
import sys
import os
from pathlib import Path


class PyPIDeployer:
    def __init__(self, repository: str = "private-pypi"):
        self.repository = repository
        self.project_root = Path(__file__).parent.parent
    
    def check_credentials(self):
        """인증 정보 확인"""
        result = subprocess.run(
            ["poetry", "config", "--list"],
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        if f"repositories.{self.repository}" not in result.stdout:
            print(f"❌ Repository '{self.repository}' not configured")
            print(f"Run: poetry config repositories.{self.repository} <URL>")
            return False
        
        if f"http-basic.{self.repository}" not in result.stdout and \
           f"pypi-token.{self.repository}" not in result.stdout:
            print(f"❌ No credentials configured for '{self.repository}'")
            print(f"Run: poetry config http-basic.{self.repository} <username> <password>")
            print(f"Or: poetry config pypi-token.{self.repository} <token>")
            return False
        
        return True
    
    def build_package(self):
        """패키지 빌드"""
        print("🏗️ Building package...")
        result = subprocess.run(
            ["poetry", "build"],
            cwd=self.project_root
        )
        
        if result.returncode != 0:
            print("❌ Build failed")
            return False
        
        print("✅ Package built successfully")
        return True
    
    def deploy(self):
        """배포 실행"""
        print(f"🚀 Deploying to {self.repository}...")
        
        result = subprocess.run(
            ["poetry", "publish", "--repository", self.repository],
            cwd=self.project_root
        )
        
        if result.returncode != 0:
            print("❌ Deployment failed")
            return False
        
        print("✅ Deployment successful")
        return True
    
    def full_deploy(self):
        """전체 배포 프로세스"""
        if not self.check_credentials():
            return False
        
        if not self.build_package():
            return False
        
        return self.deploy()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy to Private PyPI")
    parser.add_argument(
        "--repository", 
        default="private-pypi",
        help="Repository name (default: private-pypi)"
    )
    
    args = parser.parse_args()
    
    deployer = PyPIDeployer(repository=args.repository)
    
    if not deployer.full_deploy():
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 4.2 설치 스크립트

```bash
#!/bin/bash
# scripts/setup-private-pypi.sh

set -e

PYPI_SERVER_URL=${1:-"http://localhost:8080"}
USERNAME=${2:-"aegis-user"}

echo "🔧 Setting up Private PyPI configuration..."

# Repository 추가
poetry config repositories.private-pypi "$PYPI_SERVER_URL/simple/"

# 사용자 인증 정보 입력
echo "Please enter password for user '$USERNAME':"
read -s PASSWORD

poetry config http-basic.private-pypi "$USERNAME" "$PASSWORD"

echo "✅ Private PyPI configuration completed"
echo "Repository URL: $PYPI_SERVER_URL"
echo "Username: $USERNAME"

# 설정 확인
echo ""
echo "📋 Current configuration:"
poetry config --list | grep -E "(repositories|http-basic)" | grep private-pypi
```

## 5. CI/CD 통합

### 5.1 GitHub Actions

```yaml
# .github/workflows/deploy-private.yml
name: Deploy to Private PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy-private:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Configure Private PyPI
      run: |
        poetry config repositories.private-pypi ${{ secrets.PRIVATE_PYPI_URL }}
        poetry config http-basic.private-pypi ${{ secrets.PRIVATE_PYPI_USERNAME }} ${{ secrets.PRIVATE_PYPI_PASSWORD }}
    
    - name: Build and Deploy
      run: |
        poetry build
        poetry publish --repository private-pypi
```

### 5.2 GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - deploy

deploy-private:
  stage: deploy
  image: python:3.11
  before_script:
    - pip install poetry
    - poetry config repositories.private-pypi $PRIVATE_PYPI_URL
    - poetry config http-basic.private-pypi $PRIVATE_PYPI_USERNAME $PRIVATE_PYPI_PASSWORD
  script:
    - poetry build
    - poetry publish --repository private-pypi
  only:
    - tags
  variables:
    PRIVATE_PYPI_URL: "https://pypi.aegis.local/simple/"
```

## 6. 클라이언트 설정

### 6.1 pip 설정

```bash
# ~/.pip/pip.conf (Linux/Mac)
# %APPDATA%\pip\pip.ini (Windows)

[global]
extra-index-url = https://pypi.aegis.local/simple/
trusted-host = pypi.aegis.local

[install]
trusted-host = pypi.aegis.local
```

### 6.2 Poetry 클라이언트 설정

```bash
# 프로젝트에서 Private PyPI 사용
poetry source add private-pypi https://pypi.aegis.local/simple/
poetry config http-basic.private-pypi username password

# 패키지 설치
poetry add aegis-shared
```

### 6.3 requirements.txt 사용

```bash
# requirements.txt
--extra-index-url https://pypi.aegis.local/simple/
--trusted-host pypi.aegis.local
aegis-shared==0.1.0
```

## 7. 보안 고려사항

### 7.1 HTTPS 설정

```bash
# SSL 인증서 생성 (자체 서명)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 또는 Let's Encrypt 사용
certbot certonly --standalone -d pypi.aegis.local
```

### 7.2 접근 제어

```bash
# IP 기반 접근 제어 (nginx)
location / {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    
    proxy_pass http://pypi;
}
```

### 7.3 토큰 기반 인증

```python
# 토큰 생성 스크립트
import secrets
import hashlib

def generate_api_token():
    token = secrets.token_urlsafe(32)
    return token

# 사용
token = generate_api_token()
print(f"API Token: {token}")

# Poetry에 토큰 설정
# poetry config pypi-token.private-pypi <token>
```

## 8. 모니터링 및 로깅

### 8.1 로그 설정

```yaml
# docker-compose.yml에 로깅 추가
services:
  pypi-server:
    # ... 기타 설정
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 8.2 메트릭 수집

```python
# 다운로드 통계 수집 스크립트
import re
import json
from collections import defaultdict
from datetime import datetime

def parse_pypi_logs(log_file):
    """PyPI 서버 로그 파싱"""
    stats = defaultdict(int)
    
    with open(log_file, 'r') as f:
        for line in f:
            # 다운로드 패턴 매칭
            if 'GET' in line and 'aegis-shared' in line:
                stats['downloads'] += 1
    
    return dict(stats)

# 사용 예시
stats = parse_pypi_logs('/var/log/pypi/access.log')
print(json.dumps(stats, indent=2))
```

## 9. 백업 및 복구

### 9.1 패키지 백업

```bash
#!/bin/bash
# scripts/backup-packages.sh

BACKUP_DIR="/backup/pypi/$(date +%Y%m%d)"
PACKAGES_DIR="/var/pypi/packages"

mkdir -p "$BACKUP_DIR"

# 패키지 파일 백업
rsync -av "$PACKAGES_DIR/" "$BACKUP_DIR/packages/"

# 설정 파일 백업
cp /data/auth/.htpasswd "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
```

### 9.2 복구 스크립트

```bash
#!/bin/bash
# scripts/restore-packages.sh

BACKUP_DIR=$1
PACKAGES_DIR="/var/pypi/packages"

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# 패키지 복구
rsync -av "$BACKUP_DIR/packages/" "$PACKAGES_DIR/"

# 설정 복구
cp "$BACKUP_DIR/.htpasswd" /data/auth/

echo "Restore completed from: $BACKUP_DIR"
```

## 10. 트러블슈팅

### 10.1 일반적인 문제들

**문제**: 인증 실패
```bash
# 해결: 인증 정보 재설정
poetry config --unset http-basic.private-pypi
poetry config http-basic.private-pypi username password
```

**문제**: SSL 인증서 오류
```bash
# 해결: 신뢰할 수 있는 호스트 추가
poetry config certificates.private-pypi.cert /path/to/cert.pem
```

**문제**: 패키지 업로드 실패
```bash
# 해결: 권한 확인
ls -la /var/pypi/packages/
chown -R pypi:pypi /var/pypi/packages/
```

이제 Private PyPI 서버를 통해 Aegis Shared Library를 안전하게 배포하고 관리할 수 있습니다!