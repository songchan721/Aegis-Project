#!/bin/bash
# Private PyPI 서버 설정 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 기본 설정
PYPI_SERVER_URL=${1:-"https://pypi.aegis.local"}
USERNAME=${2:-"aegis-user"}
REPOSITORY_NAME=${3:-"private-pypi"}
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

log_info "Setting up Private PyPI configuration..."
log_info "Repository URL: $PYPI_SERVER_URL"
log_info "Username: $USERNAME"
log_info "Repository Name: $REPOSITORY_NAME"

# Poetry 설치 확인
if ! command -v poetry &> /dev/null; then
    log_error "Poetry is not installed. Please install Poetry first."
    log_info "Visit: https://python-poetry.org/docs/#installation"
    exit 1
fi

log_success "Poetry is installed"

# 프로젝트 디렉토리로 이동
cd "$PROJECT_ROOT"

# 디렉토리 생성
log_info "Creating necessary directories..."
mkdir -p pypi-data/packages
mkdir -p pypi-data/auth
mkdir -p nginx/ssl
mkdir -p nginx/logs
mkdir -p monitoring

log_success "Directories created"

# SSL 인증서 생성 (자체 서명)
if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
    log_info "Generating self-signed SSL certificate..."
    
    openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes \
        -subj "/C=KR/ST=Seoul/L=Seoul/O=Aegis/OU=IT Department/CN=pypi.aegis.local"
    
    log_success "SSL certificate generated"
else
    log_info "SSL certificate already exists"
fi

# htpasswd 파일 생성
if [ ! -f "pypi-data/auth/.htpasswd" ]; then
    log_info "Creating authentication file..."
    
    # htpasswd 설치 확인
    if ! command -v htpasswd &> /dev/null; then
        log_warning "htpasswd not found. Installing apache2-utils..."
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y apache2-utils
        elif command -v yum &> /dev/null; then
            sudo yum install -y httpd-tools
        elif command -v brew &> /dev/null; then
            brew install httpd
        else
            log_error "Cannot install htpasswd. Please install it manually."
            exit 1
        fi
    fi
    
    echo "Please enter password for user '$USERNAME':"
    htpasswd -c pypi-data/auth/.htpasswd "$USERNAME"
    
    log_success "Authentication file created"
else
    log_info "Authentication file already exists"
fi

# Poetry repository 설정
log_info "Configuring Poetry repository..."

# Repository URL 설정
poetry config repositories."$REPOSITORY_NAME" "$PYPI_SERVER_URL/simple/"

# 인증 방식 선택
echo ""
echo "Choose authentication method:"
echo "1) Username/Password"
echo "2) API Token"
read -p "Enter choice (1 or 2): " auth_choice

case $auth_choice in
    1)
        echo "Please enter password for user '$USERNAME':"
        read -s PASSWORD
        poetry config http-basic."$REPOSITORY_NAME" "$USERNAME" "$PASSWORD"
        log_success "Username/password authentication configured"
        ;;
    2)
        echo "Please enter API token:"
        read -s TOKEN
        poetry config pypi-token."$REPOSITORY_NAME" "$TOKEN"
        log_success "Token authentication configured"
        ;;
    *)
        log_error "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

# Prometheus 설정 파일 생성
log_info "Creating monitoring configuration..."

cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'pypi-server'
    static_configs:
      - targets: ['pypi-server:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    metrics_path: '/metrics'
    scrape_interval: 30s
EOF

# Docker Compose 환경 변수 파일 생성
cat > .env.pypi << EOF
# Private PyPI Server Configuration
PYPI_SERVER_URL=$PYPI_SERVER_URL
PYPI_USERNAME=$USERNAME
PYPI_REPOSITORY=$REPOSITORY_NAME

# Docker Configuration
COMPOSE_PROJECT_NAME=aegis-pypi
COMPOSE_FILE=docker-compose.pypi.yml

# Nginx Configuration
NGINX_HOST=pypi.aegis.local
NGINX_PORT=443

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
EOF

log_success "Configuration files created"

# 설정 확인
log_info "Verifying Poetry configuration..."
echo ""
echo "📋 Current Poetry configuration:"
poetry config --list | grep -E "(repositories|http-basic|pypi-token)" | grep "$REPOSITORY_NAME" || true

# Docker Compose 파일 존재 확인
if [ -f "docker-compose.pypi.yml" ]; then
    log_success "Docker Compose configuration found"
    
    echo ""
    echo "🐳 To start the Private PyPI server:"
    echo "   docker-compose -f docker-compose.pypi.yml up -d"
    echo ""
    echo "🔍 To check server status:"
    echo "   docker-compose -f docker-compose.pypi.yml ps"
    echo ""
    echo "📦 To deploy packages:"
    echo "   python scripts/deploy-private.py --repository $REPOSITORY_NAME"
    echo ""
    echo "🛑 To stop the server:"
    echo "   docker-compose -f docker-compose.pypi.yml down"
else
    log_warning "Docker Compose configuration not found"
fi

# 추가 설정 안내
echo ""
echo "📝 Additional setup steps:"
echo "1. Add 'pypi.aegis.local' to your /etc/hosts file:"
echo "   echo '127.0.0.1 pypi.aegis.local' | sudo tee -a /etc/hosts"
echo ""
echo "2. Configure pip to use the private repository:"
echo "   pip config set global.extra-index-url $PYPI_SERVER_URL/simple/"
echo "   pip config set global.trusted-host pypi.aegis.local"
echo ""
echo "3. Install packages from private repository:"
echo "   pip install aegis-shared --extra-index-url $PYPI_SERVER_URL/simple/"

log_success "Private PyPI setup completed!"

# 테스트 연결 (선택적)
read -p "Do you want to test the connection? (y/n): " test_connection

if [ "$test_connection" = "y" ] || [ "$test_connection" = "Y" ]; then
    log_info "Testing connection to $PYPI_SERVER_URL..."
    
    if curl -k -s "$PYPI_SERVER_URL/simple/" > /dev/null; then
        log_success "Connection test successful!"
    else
        log_warning "Connection test failed. Make sure the server is running."
    fi
fi