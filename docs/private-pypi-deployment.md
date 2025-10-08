# Private PyPI 배포 가이드

이 문서는 Aegis Shared Library를 Private PyPI 서버에 배포하고 관리하는 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [Private PyPI 서버 설정](#private-pypi-서버-설정)
3. [클라이언트 설정](#클라이언트-설정)
4. [패키지 배포](#패키지-배포)
5. [버전 관리](#버전-관리)
6. [CI/CD 통합](#cicd-통합)
7. [모니터링](#모니터링)
8. [트러블슈팅](#트러블슈팅)

## 개요

Private PyPI는 조직 내부에서 Python 패키지를 안전하게 배포하고 관리할 수 있는 솔루션입니다.

### 주요 기능

- 🔒 **보안**: 내부 네트워크에서만 접근 가능
- 📦 **패키지 관리**: 버전별 패키지 저장 및 관리
- 🚀 **자동 배포**: CI/CD 파이프라인 통합
- 📊 **모니터링**: 다운로드 통계 및 서버 상태 모니터링
- 🔄 **버전 관리**: 자동 버전 업데이트 및 릴리스

## Private PyPI 서버 설정

### 1. Docker Compose를 사용한 설정 (권장)

```bash
# 1. 설정 스크립트 실행
bash scripts/setup-private-pypi.sh

# 2. 서버 시작
make pypi-server-start

# 3. 서버 상태 확인
make pypi-server-status
```

### 2. 수동 설정

#### 2.1 디렉토리 구조 생성

```bash
mkdir -p pypi-data/{packages,auth}
mkdir -p nginx/{ssl,logs}
mkdir -p monitoring
```

#### 2.2 인증 파일 생성

```bash
# htpasswd 설치 (Ubuntu/Debian)
sudo apt-get install apache2-utils

# 사용자 생성
htpasswd -c pypi-data/auth/.htpasswd aegis-user
```

#### 2.3 SSL 인증서 생성

```bash
# 자체 서명 인증서 생성
openssl req -x509 -newkey rsa:4096 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -days 365 -nodes \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Aegis/CN=pypi.aegis.local"
```

#### 2.4 서버 시작

```bash
docker-compose -f docker-compose.pypi.yml up -d
```

### 3. 서버 구성 요소

| 서비스 | 포트 | 설명 |
|--------|------|------|
| pypi-server | 8080 | PyPI 서버 (내부) |
| nginx | 80, 443 | 리버스 프록시 및 SSL |
| redis | 6379 | 캐싱 (선택적) |
| prometheus | 9090 | 메트릭 수집 |
| grafana | 3000 | 모니터링 대시보드 |

## 클라이언트 설정

### 1. Poetry 설정

```bash
# Repository 추가
poetry config repositories.private-pypi https://pypi.aegis.local/simple/

# 인증 정보 설정 (사용자명/비밀번호)
poetry config http-basic.private-pypi aegis-user your-password

# 또는 토큰 사용
poetry config pypi-token.private-pypi your-api-token
```

### 2. pip 설정

```bash
# ~/.pip/pip.conf 파일 생성
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << EOF
[global]
extra-index-url = https://pypi.aegis.local/simple/
trusted-host = pypi.aegis.local

[install]
trusted-host = pypi.aegis.local
EOF
```

### 3. hosts 파일 설정

```bash
# /etc/hosts에 추가
echo "127.0.0.1 pypi.aegis.local" | sudo tee -a /etc/hosts
```

## 패키지 배포

### 1. 기본 배포

```bash
# 스크립트 사용
python scripts/deploy-private.py

# 또는 Makefile 사용
make publish-private
```

### 2. 버전 업데이트와 함께 배포

```bash
# 패치 버전 업데이트 후 배포
python scripts/deploy-private.py --bump patch

# 또는 Makefile 사용
make publish-private-bump-patch
make publish-private-bump-minor
make publish-private-bump-major
```

### 3. 강제 배포 (기존 버전 덮어쓰기)

```bash
python scripts/deploy-private.py --force
```

### 4. 빌드 스킵 배포

```bash
python scripts/deploy-private.py --skip-build
```

## 버전 관리

### 1. 자동 버전 관리

```bash
# 커밋 내용을 분석하여 자동으로 버전 타입 결정
python scripts/version-manager.py release auto

# 태그 푸시와 함께
python scripts/version-manager.py release auto --push-tag
```

### 2. 수동 버전 관리

```bash
# 특정 버전 타입으로 업데이트
python scripts/version-manager.py bump patch
python scripts/version-manager.py bump minor
python scripts/version-manager.py bump major

# 프리릴리스 버전
python scripts/version-manager.py bump prerelease --prerelease-type alpha
```

### 3. CHANGELOG 자동 생성

```bash
# 현재 버전의 CHANGELOG 생성
python scripts/version-manager.py changelog 1.2.3
```

### 4. 전체 릴리스 프로세스

```bash
# 버전 업데이트 + CHANGELOG + Git 태그 + 배포
make version-release
```

## CI/CD 통합

### 1. GitHub Actions 설정

프로젝트의 `.github/workflows/ci.yml`에 이미 Private PyPI 배포가 구성되어 있습니다.

#### 필요한 Secrets

| Secret | 설명 |
|--------|------|
| `PRIVATE_PYPI_URL` | Private PyPI 서버 URL |
| `PRIVATE_PYPI_USERNAME` | 사용자명 |
| `PRIVATE_PYPI_PASSWORD` | 비밀번호 |

#### 배포 트리거

- **main 브랜치**: Private PyPI에 자동 배포
- **develop 브랜치**: Test PyPI에 배포
- **태그 푸시**: GitHub Release 생성 및 배포

### 2. 로컬 개발 워크플로우

```bash
# 1. 개발 완료 후 커밋
git add .
git commit -m "feat: add new feature"

# 2. 버전 업데이트 및 태그 생성
make version-release

# 3. 변경사항 푸시
git push origin main --tags

# 4. Private PyPI에 배포
make publish-private
```

## 모니터링

### 1. 서버 상태 확인

```bash
# Docker 컨테이너 상태
make pypi-server-status

# 로그 확인
make pypi-server-logs

# 헬스 체크
curl -k https://pypi.aegis.local/health
```

### 2. Prometheus 메트릭

Prometheus는 `http://localhost:9090`에서 접근 가능합니다.

주요 메트릭:
- HTTP 요청 수 및 응답 시간
- 패키지 다운로드 통계
- 서버 리소스 사용량

### 3. Grafana 대시보드

Grafana는 `http://localhost:3000`에서 접근 가능합니다.

기본 로그인:
- 사용자명: `admin`
- 비밀번호: `admin123`

### 4. 로그 분석

```bash
# PyPI 서버 로그
docker-compose -f docker-compose.pypi.yml logs pypi-server

# Nginx 액세스 로그
docker-compose -f docker-compose.pypi.yml exec nginx tail -f /var/log/nginx/access.log
```

## 패키지 설치

### 1. Private PyPI에서 설치

```bash
# pip 사용
pip install aegis-shared --extra-index-url https://pypi.aegis.local/simple/

# Poetry 사용 (pyproject.toml에 소스 추가)
poetry add aegis-shared
```

### 2. 특정 버전 설치

```bash
pip install aegis-shared==1.2.3 --extra-index-url https://pypi.aegis.local/simple/
```

### 3. requirements.txt 사용

```txt
--extra-index-url https://pypi.aegis.local/simple/
--trusted-host pypi.aegis.local
aegis-shared==1.2.3
```

## 보안 고려사항

### 1. 네트워크 보안

- VPN 또는 내부 네트워크에서만 접근 허용
- 방화벽 규칙으로 IP 제한
- SSL/TLS 암호화 사용

### 2. 인증 및 권한

```bash
# 사용자별 권한 설정
htpasswd -B pypi-data/auth/.htpasswd user1
htpasswd -B pypi-data/auth/.htpasswd user2

# 읽기 전용 사용자 생성 (다운로드만 가능)
# pypi-server 설정에서 -a download,list 옵션 사용
```

### 3. 패키지 무결성

```bash
# 패키지 서명 확인
pip install --trusted-host pypi.aegis.local --verify-signature aegis-shared
```

## 백업 및 복구

### 1. 패키지 백업

```bash
# 백업 스크립트 실행
bash scripts/backup-packages.sh

# 수동 백업
rsync -av pypi-data/packages/ /backup/pypi-packages/
```

### 2. 설정 백업

```bash
# 인증 파일 백업
cp pypi-data/auth/.htpasswd /backup/
cp docker-compose.pypi.yml /backup/
cp nginx/nginx.conf /backup/
```

### 3. 복구

```bash
# 패키지 복구
bash scripts/restore-packages.sh /backup/pypi-packages/

# 서비스 재시작
make pypi-server-stop
make pypi-server-start
```

## 트러블슈팅

### 1. 일반적인 문제

#### 인증 실패

```bash
# 문제: 401 Unauthorized
# 해결: 인증 정보 재설정
poetry config --unset http-basic.private-pypi
poetry config http-basic.private-pypi username password
```

#### SSL 인증서 오류

```bash
# 문제: SSL certificate verify failed
# 해결: 인증서 신뢰 설정
pip config set global.trusted-host pypi.aegis.local
```

#### 패키지 업로드 실패

```bash
# 문제: 403 Forbidden
# 해결: 권한 확인
ls -la pypi-data/packages/
sudo chown -R 1000:1000 pypi-data/packages/
```

### 2. 로그 확인

```bash
# PyPI 서버 로그
docker-compose -f docker-compose.pypi.yml logs pypi-server

# Nginx 에러 로그
docker-compose -f docker-compose.pypi.yml logs nginx
```

### 3. 연결 테스트

```bash
# 서버 연결 테스트
curl -k https://pypi.aegis.local/simple/

# 패키지 검색
curl -k https://pypi.aegis.local/simple/aegis-shared/
```

### 4. 디버그 모드

```bash
# PyPI 서버 디버그 모드로 실행
docker-compose -f docker-compose.pypi.yml exec pypi-server \
  pypi-server -p 8080 -P /data/auth/.htpasswd -a update,download,list -v /data/packages
```

## 고급 설정

### 1. 다중 인덱스 설정

```toml
# pyproject.toml
[[tool.poetry.source]]
name = "private-pypi"
url = "https://pypi.aegis.local/simple/"
priority = "primary"

[[tool.poetry.source]]
name = "pypi"
url = "https://pypi.org/simple/"
priority = "supplemental"
```

### 2. 패키지별 소스 지정

```toml
[tool.poetry.dependencies]
aegis-shared = {version = "^1.0.0", source = "private-pypi"}
requests = "^2.28.0"  # 공개 PyPI에서
```

### 3. 환경별 설정

```bash
# 개발 환경
export PYPI_INDEX_URL="https://pypi.aegis.local/simple/"

# 프로덕션 환경
export PYPI_INDEX_URL="https://pypi.prod.aegis.local/simple/"
```

이제 Private PyPI 서버를 통해 Aegis Shared Library를 안전하고 효율적으로 배포할 수 있습니다! 🚀