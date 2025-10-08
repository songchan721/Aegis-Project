#!/bin/bash

# Aegis CI/CD 설정 스크립트

set -e

echo "🚀 Aegis CI/CD 환경 설정 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 필수 도구 확인
check_requirements() {
    log_info "필수 도구 확인 중..."
    
    # Python 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3이 설치되지 않았습니다."
        exit 1
    fi
    
    # Poetry 확인
    if ! command -v poetry &> /dev/null; then
        log_warn "Poetry가 설치되지 않았습니다. 설치를 진행합니다..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        log_warn "Docker가 설치되지 않았습니다."
    fi
    
    # Git 확인
    if ! command -v git &> /dev/null; then
        log_error "Git이 설치되지 않았습니다."
        exit 1
    fi
    
    log_info "필수 도구 확인 완료"
}

# Poetry 환경 설정
setup_poetry() {
    log_info "Poetry 환경 설정 중..."
    
    # Poetry 설정
    poetry config virtualenvs.create true
    poetry config virtualenvs.in-project true
    
    # 의존성 설치
    if [ -f "pyproject.toml" ]; then
        log_info "Shared Library 의존성 설치 중..."
        poetry install
    fi
    
    log_info "Poetry 환경 설정 완료"
}

# 개발 도구 설정
setup_dev_tools() {
    log_info "개발 도구 설정 중..."
    
    # Pre-commit hooks 설치
    if [ -f ".pre-commit-config.yaml" ]; then
        poetry run pre-commit install
        log_info "Pre-commit hooks 설치 완료"
    fi
    
    # 코드 품질 도구 설정
    poetry run flake8 --version > /dev/null 2>&1 || poetry add --group dev flake8
    poetry run mypy --version > /dev/null 2>&1 || poetry add --group dev mypy
    poetry run bandit --version > /dev/null 2>&1 || poetry add --group dev bandit
    poetry run pytest --version > /dev/null 2>&1 || poetry add --group dev pytest
    
    log_info "개발 도구 설정 완료"
}

# 테스트 환경 설정
setup_test_env() {
    log_info "테스트 환경 설정 중..."
    
    # 테스트 데이터베이스 설정
    if command -v docker &> /dev/null; then
        log_info "테스트용 PostgreSQL 컨테이너 시작..."
        docker run -d \
            --name aegis-test-postgres \
            -e POSTGRES_PASSWORD=test \
            -e POSTGRES_DB=test_db \
            -p 5433:5432 \
            postgres:15 || log_warn "PostgreSQL 컨테이너가 이미 실행 중입니다."
        
        log_info "테스트용 Redis 컨테이너 시작..."
        docker run -d \
            --name aegis-test-redis \
            -p 6380:6379 \
            redis:7-alpine || log_warn "Redis 컨테이너가 이미 실행 중입니다."
    fi
    
    log_info "테스트 환경 설정 완료"
}

# GitHub Actions 시크릿 가이드
show_secrets_guide() {
    log_info "GitHub Actions 시크릿 설정 가이드:"
    echo ""
    echo "다음 시크릿들을 GitHub 저장소 설정에서 추가해주세요:"
    echo ""
    echo "📦 Private PyPI 설정:"
    echo "  - PRIVATE_PYPI_URL: Private PyPI 서버 URL"
    echo "  - PRIVATE_PYPI_USERNAME: Private PyPI 사용자명"
    echo "  - PRIVATE_PYPI_PASSWORD: Private PyPI 비밀번호"
    echo ""
    echo "📢 알림 설정:"
    echo "  - SLACK_WEBHOOK_URL: Slack 웹훅 URL (선택사항)"
    echo ""
    echo "🔐 기타 시크릿:"
    echo "  - CODECOV_TOKEN: Codecov 토큰 (선택사항)"
    echo ""
}

# 로컬 테스트 실행
run_local_tests() {
    log_info "로컬 테스트 실행 중..."
    
    # Shared Library 테스트
    if [ -f "pyproject.toml" ]; then
        log_info "Shared Library 테스트 실행..."
        poetry run pytest tests/ -v --cov=aegis_shared || log_warn "일부 테스트가 실패했습니다."
    fi
    
    # User Service 테스트
    if [ -d "user-service" ]; then
        log_info "User Service 테스트 실행..."
        cd user-service
        python -m pytest tests/ -v || log_warn "User Service 테스트가 실패했습니다."
        cd ..
    fi
    
    log_info "로컬 테스트 완료"
}

# 메인 실행
main() {
    echo "🎯 Aegis CI/CD 설정 스크립트"
    echo "=============================="
    
    check_requirements
    setup_poetry
    setup_dev_tools
    setup_test_env
    
    echo ""
    show_secrets_guide
    
    echo ""
    read -p "로컬 테스트를 실행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_local_tests
    fi
    
    echo ""
    log_info "✅ CI/CD 설정이 완료되었습니다!"
    echo ""
    echo "다음 단계:"
    echo "1. GitHub 저장소에 시크릿 추가"
    echo "2. 코드를 커밋하고 푸시"
    echo "3. GitHub Actions에서 빌드 확인"
    echo ""
}

# 스크립트 실행
main "$@"