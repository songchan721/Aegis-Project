# CI/CD Guide - Aegis Shared Library

## 개요

Aegis Shared Library는 GitHub Actions를 활용한 완전 자동화된 CI/CD 파이프라인을 제공합니다.

## CI/CD 워크플로우

### 1. 자동 테스트 및 빌드 (shared-library-ci.yml)

코드를 `main` 또는 `develop` 브랜치에 푸시하거나 PR을 생성하면 자동으로 실행됩니다.

#### 트리거 조건

- **Push**: `main`, `develop` 브랜치에 푸시
- **Pull Request**: `main`, `develop` 브랜치로의 PR
- **파일 경로**:
  - `aegis_shared/**`
  - `pyproject.toml`
  - `poetry.lock`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `.github/workflows/shared-library-ci.yml`

#### 파이프라인 단계

##### 1️⃣ Test Suite (테스트 실행)

```yaml
Environment:
  - Python 3.11
  - PostgreSQL 15
  - Redis 7
```

**실행 단계:**
1. 코드 체크아웃
2. Python 및 Poetry 설치
3. 의존성 설치 (캐싱 지원)
4. libmagic 시스템 패키지 설치
5. 전체 테스트 실행 (252 tests)
6. 커버리지 측정 (80% 이상 요구)
7. Codecov 업로드
8. 테스트 결과 아티팩트 업로드

**환경 변수:**
- `DATABASE_URL`: PostgreSQL 연결 URL
- `REDIS_URL`: Redis 연결 URL
- `JWT_SECRET_KEY`: JWT 테스트용 시크릿
- `JWT_ALGORITHM`: HS256
- `ENVIRONMENT`: test

##### 2️⃣ Code Quality Checks (코드 품질 검사)

**도구:**
- **Black**: 코드 포맷팅 검사
- **isort**: Import 정렬 검사
- **Flake8**: 린팅 (문법 및 스타일 검사)
- **MyPy**: 타입 힌팅 검사

모든 코드 품질 검사는 `continue-on-error: true`로 설정되어 있어 실패해도 파이프라인이 중단되지 않습니다.

##### 3️⃣ Build Package (패키지 빌드)

**단계:**
1. Poetry를 사용하여 패키지 빌드
2. Twine으로 패키지 검증
3. 빌드 아티팩트 업로드 (`dist/` 디렉토리)

**빌드 결과:**
- Wheel 파일 (`.whl`)
- Source distribution (`.tar.gz`)

##### 4️⃣ Security Scan (보안 스캔)

**도구:**
- **Bandit**: Python 코드 보안 취약점 검사
- **Safety**: 의존성 패키지 취약점 검사
- **Trivy**: 파일시스템 전체 취약점 스캔

**결과:**
- JSON 형식의 보안 리포트
- SARIF 형식으로 GitHub Security 탭에 업로드

##### 5️⃣ Publish Package (패키지 배포)

**트리거:** Release 이벤트 (published)

**조건:**
- 모든 이전 작업이 성공해야 함
- Release가 published 상태여야 함

**배포 단계:**
1. 빌드 아티팩트 다운로드
2. Private PyPI 설정 (시크릿 설정 시)
3. 패키지 배포
4. GitHub Release에 빌드 파일 첨부

**필요한 Secrets:**
- `PRIVATE_PYPI_URL`: Private PyPI 서버 URL
- `PRIVATE_PYPI_USERNAME`: PyPI 사용자명
- `PRIVATE_PYPI_PASSWORD`: PyPI 비밀번호

##### 6️⃣ Notify Teams (알림)

**트리거:** 모든 작업 완료 후 (성공/실패 여부와 무관)

**알림 방법:**
- Slack Webhook (설정 시)

**필요한 Secret:**
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

---

### 2. 릴리스 관리 (release.yml)

버전 관리 및 릴리스 자동화를 위한 수동 워크플로우입니다.

#### 트리거 방법

GitHub Actions 탭에서 "Release Management" 워크플로우를 수동 실행:

1. **Actions** 탭으로 이동
2. **Release Management** 선택
3. **Run workflow** 클릭
4. 파라미터 입력:
   - **version_bump**: `patch`, `minor`, 또는 `major`
   - **prerelease**: Pre-release 여부 (체크박스)

#### 버전 범프 타입

| 타입 | 현재 버전 | 새 버전 | 사용 시기 |
|------|-----------|---------|-----------|
| `patch` | 0.1.0 | 0.1.1 | 버그 수정 |
| `minor` | 0.1.0 | 0.2.0 | 새로운 기능 추가 (하위 호환) |
| `major` | 0.1.0 | 1.0.0 | Breaking changes |

#### 릴리스 프로세스

1. **버전 범프**: `pyproject.toml`의 버전 업데이트
2. **CHANGELOG 업데이트**: 자동으로 변경 이력 추가
3. **커밋 및 푸시**: 버전 변경사항 커밋
4. **Git 태그 생성**: `v{version}` 형식의 태그 생성
5. **릴리스 노트 생성**: 
   - 커밋 히스토리 기반 자동 생성
   - 설치 방법 포함
   - 테스트 상태 포함
6. **GitHub Release 생성**: 릴리스 페이지에 자동 게시

#### 릴리스 노트 포맷

```markdown
# Aegis Shared Library v{VERSION}

## 🚀 What's Changed
- 커밋 메시지 목록 (해시 포함)

## 📦 Installation
poetry add aegis-shared@{VERSION}
pip install aegis-shared=={VERSION}

## 📊 Test Coverage
- ✅ 252 tests passed
- 📈 80%+ code coverage
- 🔒 Security scans passed

## 🔗 Links
- Documentation
- Changelog
```

---

## GitHub Secrets 설정

### 필수 Secrets

없음 (기본 `GITHUB_TOKEN`만 사용)

### 선택적 Secrets (기능 활성화)

#### Private PyPI 배포

```
PRIVATE_PYPI_URL=https://pypi.your-company.com
PRIVATE_PYPI_USERNAME=your-username
PRIVATE_PYPI_PASSWORD=your-password
```

#### Slack 알림

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Secrets 설정 방법

1. GitHub 저장소 페이지로 이동
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** 클릭
4. Secret 이름과 값 입력
5. **Add secret** 클릭

---

## 로컬에서 CI 재현하기

### 테스트 실행

```bash
# 전체 테스트 실행
poetry run pytest aegis_shared/tests/ -v --cov=aegis_shared --cov-report=term-missing

# 커버리지 임계값 확인 (80%)
poetry run coverage report --fail-under=80
```

### 코드 품질 검사

```bash
# Black 포맷 검사
poetry run black --check aegis_shared/

# Black 자동 포맷
poetry run black aegis_shared/

# isort 검사
poetry run isort --check-only aegis_shared/

# isort 자동 정렬
poetry run isort aegis_shared/

# Flake8 린팅
poetry run flake8 aegis_shared/ --max-line-length=100

# MyPy 타입 검사
poetry run mypy aegis_shared/ --ignore-missing-imports
```

### 보안 스캔

```bash
# Bandit 보안 스캔
poetry add --group dev bandit
poetry run bandit -r aegis_shared/

# Safety 의존성 스캔
poetry add --group dev safety
poetry run safety check
```

### 패키지 빌드

```bash
# 패키지 빌드
poetry build

# 빌드 결과 검증
poetry run pip install twine
poetry run twine check dist/*
```

---

## 브랜치 전략

### main 브랜치

- **보호됨**: 직접 푸시 금지
- **PR 필수**: 모든 변경사항은 PR을 통해서만 병합
- **CI 통과 필수**: 모든 테스트와 검사가 통과해야 병합 가능
- **릴리스 기준**: `main` 브랜치가 항상 배포 가능한 상태 유지

### develop 브랜치

- **개발 브랜치**: 모든 기능 개발의 기준
- **CI 실행**: 푸시 시 자동으로 CI 실행
- **머지 전략**: Feature 브랜치를 `develop`으로 병합

### Feature 브랜치

- **네이밍**: `feature/{feature-name}`
- **기준 브랜치**: `develop`에서 분기
- **병합 대상**: `develop`으로 PR

---

## CI/CD 최적화 팁

### 1. 캐싱 활용

Poetry 의존성은 자동으로 캐싱됩니다:
- 캐시 키: `venv-{OS}-{Python버전}-{poetry.lock 해시}`
- 의존성이 변경되지 않으면 설치 단계 스킵

### 2. 병렬 실행

다음 작업들은 병렬로 실행됩니다:
- Code Quality Checks
- Build Package
- Security Scan

### 3. 조건부 실행

- Publish: Release 이벤트에서만 실행
- Notify: Slack Webhook이 설정된 경우에만 실행

### 4. Fail-fast 전략

- 테스트 실패 시 즉시 파이프라인 중단
- 커버리지 80% 미달 시 실패

---

## 트러블슈팅

### 문제: 테스트가 로컬에서는 통과하는데 CI에서 실패

**원인:**
- 환경 변수 누락
- PostgreSQL/Redis 연결 실패
- 의존성 버전 차이

**해결:**
1. CI 로그에서 정확한 에러 확인
2. 환경 변수가 올바르게 설정되었는지 확인
3. `poetry.lock` 파일이 최신인지 확인

### 문제: 캐시가 작동하지 않음

**원인:**
- `poetry.lock` 파일이 변경됨

**해결:**
1. 의존성 변경 시 `poetry.lock` 커밋
2. 캐시를 무효화하려면 PR 설명에 `[no cache]` 추가

### 문제: Private PyPI 배포 실패

**원인:**
- Secrets가 설정되지 않음
- PyPI 서버 연결 실패

**해결:**
1. GitHub Secrets 설정 확인
2. PyPI URL이 올바른지 확인
3. 인증 정보가 유효한지 확인

### 문제: 릴리스 워크플로우 실행 안 됨

**원인:**
- 수동 워크플로우는 기본적으로 `main` 브랜치에서만 실행 가능

**해결:**
1. `main` 브랜치 선택 확인
2. 워크플로우 파일이 `main`에 병합되었는지 확인

---

## 참고 자료

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [Poetry 공식 문서](https://python-poetry.org/docs/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 다음 단계

1. **브랜치 보호 규칙 설정**: GitHub 저장소 설정에서 `main` 브랜치 보호
2. **Secrets 설정**: Private PyPI 및 Slack Webhook 설정
3. **첫 릴리스 생성**: Release Management 워크플로우 실행
4. **CI 배지 추가**: README.md에 CI 상태 배지 추가

### CI 배지 예시

```markdown
[![CI/CD](https://github.com/{owner}/{repo}/actions/workflows/shared-library-ci.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/shared-library-ci.yml)
```
