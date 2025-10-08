# Aegis Project Makefile

.PHONY: help install test lint format clean build deploy

# 기본 변수
PYTHON_VERSION := 3.11
POETRY := poetry
DOCKER := docker
DOCKER_COMPOSE := docker-compose

# 색상 정의
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 사용 가능한 명령어 표시
	@echo "$(GREEN)Aegis Project Makefile$(NC)"
	@echo "======================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# 설치 및 설정
install: ## Poetry 의존성 설치
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(POETRY) install
	$(POETRY) run pre-commit install

install-dev: ## 개발 의존성 포함 설치
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(POETRY) install --with dev
	$(POETRY) run pre-commit install

# 코드 품질
lint: ## 코드 린팅 실행
	@echo "$(GREEN)Running linting...$(NC)"
	$(POETRY) run flake8 aegis_shared/
	$(POETRY) run mypy aegis_shared/
	$(POETRY) run bandit -r aegis_shared/

format: ## 코드 포맷팅 실행
	@echo "$(GREEN)Formatting code...$(NC)"
	$(POETRY) run black aegis_shared/ tests/
	$(POETRY) run isort aegis_shared/ tests/

format-check: ## 코드 포맷팅 체크
	@echo "$(GREEN)Checking code format...$(NC)"
	$(POETRY) run black --check aegis_shared/ tests/
	$(POETRY) run isort --check-only aegis_shared/ tests/

# 테스트
test: ## 모든 테스트 실행
	@echo "$(GREEN)Running all tests...$(NC)"
	$(POETRY) run pytest tests/ -v

test-unit: ## 단위 테스트만 실행
	@echo "$(GREEN)Running unit tests...$(NC)"
	$(POETRY) run pytest tests/unit/ -v

test-integration: ## 통합 테스트만 실행
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/integration/ -v

test-performance: ## 성능 테스트 실행
	@echo "$(GREEN)Running performance tests...$(NC)"
	$(POETRY) run pytest tests/performance/ -v

test-coverage: ## 커버리지와 함께 테스트 실행
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(POETRY) run pytest tests/ --cov=aegis_shared --cov-report=html --cov-report=term

test-user-service: ## User Service 테스트 실행
	@echo "$(GREEN)Running User Service tests...$(NC)"
	cd user-service && python -m pytest tests/ -v

# 빌드
build: ## 패키지 빌드
	@echo "$(GREEN)Building package...$(NC)"
	$(POETRY) build

build-docker: ## Docker 이미지 빌드
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(DOCKER) build -t aegis-shared:latest .
	cd user-service && $(DOCKER) build -t user-service:latest .

# 배포
publish: ## Private PyPI에 패키지 배포
	@echo "$(GREEN)Publishing to private PyPI...$(NC)"
	$(POETRY) publish --repository private

publish-test: ## 테스트 PyPI에 패키지 배포
	@echo "$(GREEN)Publishing to test PyPI...$(NC)"
	$(POETRY) publish --repository testpypi

# 개발 환경
dev-setup: ## 개발 환경 설정
	@echo "$(GREEN)Setting up development environment...$(NC)"
	./scripts/ci-setup.sh

dev-services: ## 개발용 서비스 시작 (PostgreSQL, Redis, Kafka)
	@echo "$(GREEN)Starting development services...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml up -d

dev-services-stop: ## 개발용 서비스 중지
	@echo "$(GREEN)Stopping development services...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml down

# 샘플 서비스
sample-service: ## 샘플 서비스 실행
	@echo "$(GREEN)Starting sample service...$(NC)"
	cd examples/sample-service && $(DOCKER_COMPOSE) up -d

sample-service-test: ## 샘플 서비스 테스트
	@echo "$(GREEN)Testing sample service...$(NC)"
	cd examples/sample-service && python -m pytest tests/ -v

# User Service
user-service: ## User Service 실행
	@echo "$(GREEN)Starting User Service...$(NC)"
	cd user-service && $(DOCKER_COMPOSE) up -d

user-service-logs: ## User Service 로그 확인
	@echo "$(GREEN)Showing User Service logs...$(NC)"
	cd user-service && $(DOCKER_COMPOSE) logs -f user-service

# 벤치마크
benchmark: ## 성능 벤치마크 실행
	@echo "$(GREEN)Running performance benchmark...$(NC)"
	cd examples/sample-service && python tests/performance/benchmark.py

# 정리
clean: ## 빌드 아티팩트 정리
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

clean-docker: ## Docker 이미지 및 컨테이너 정리
	@echo "$(GREEN)Cleaning Docker resources...$(NC)"
	$(DOCKER) system prune -f
	$(DOCKER) volume prune -f

# 문서
docs: ## 문서 생성
	@echo "$(GREEN)Generating documentation...$(NC)"
	$(POETRY) run sphinx-build -b html docs/ docs/_build/

docs-serve: ## 문서 서버 실행
	@echo "$(GREEN)Starting documentation server...$(NC)"
	cd docs/_build/html && python -m http.server 8080

# 보안
security-scan: ## 보안 스캔 실행
	@echo "$(GREEN)Running security scan...$(NC)"
	$(POETRY) run bandit -r aegis_shared/ -f json -o bandit-report.json
	$(POETRY) run safety check

# 전체 CI 파이프라인 로컬 실행
ci-local: format-check lint test-coverage security-scan build ## 로컬에서 전체 CI 파이프라인 실행
	@echo "$(GREEN)✅ All CI checks passed!$(NC)"

# 릴리스 준비
release-prepare: ## 릴리스 준비 (버전 업데이트, 태그 생성)
	@echo "$(GREEN)Preparing release...$(NC)"
	$(POETRY) run python scripts/version-manager.py bump
	git add pyproject.toml
	git commit -m "chore: bump version"
	git tag v$$($(POETRY) version -s)

release-notes: ## 릴리스 노트 생성
	@echo "$(GREEN)Generating release notes...$(NC)"
	$(POETRY) run python scripts/generate-release-notes.py

# 모니터링
health-check: ## 서비스 헬스 체크
	@echo "$(GREEN)Checking service health...$(NC)"
	curl -f http://localhost:8000/health || echo "$(RED)Sample service is not running$(NC)"
	curl -f http://localhost:8001/health || echo "$(RED)User service is not running$(NC)"

logs: ## 모든 서비스 로그 확인
	@echo "$(GREEN)Showing all service logs...$(NC)"
	$(DOCKER_COMPOSE) logs -f

# 기본 타겟
all: install lint test build ## 모든 기본 작업 실행

.DEFAULT_GOAL := help