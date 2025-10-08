# Private PyPI 서버 설정 스크립트 (PowerShell)

param(
    [string]$PyPIServerURL = "https://pypi.aegis.local",
    [string]$Username = "aegis-user",
    [string]$RepositoryName = "private-pypi"
)

# 색상 함수
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

Write-Info "Setting up Private PyPI configuration..."
Write-Info "Repository URL: $PyPIServerURL"
Write-Info "Username: $Username"
Write-Info "Repository Name: $RepositoryName"

# Poetry 설치 확인
try {
    $poetryVersion = poetry --version
    Write-Success "Poetry is installed: $poetryVersion"
} catch {
    Write-Error "Poetry is not installed. Please install Poetry first."
    Write-Info "Visit: https://python-poetry.org/docs/#installation"
    exit 1
}

# 프로젝트 루트 디렉토리
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 디렉토리 생성
Write-Info "Creating necessary directories..."
$directories = @(
    "pypi-data\packages",
    "pypi-data\auth",
    "nginx\ssl",
    "nginx\logs",
    "monitoring"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "Directories created"

# SSL 인증서 생성 (OpenSSL 필요)
if (!(Test-Path "nginx\ssl\cert.pem") -or !(Test-Path "nginx\ssl\key.pem")) {
    Write-Info "Generating self-signed SSL certificate..."
    
    try {
        # OpenSSL 명령어 실행
        $opensslCmd = "openssl req -x509 -newkey rsa:4096 -keyout nginx\ssl\key.pem -out nginx\ssl\cert.pem -days 365 -nodes -subj `"/C=KR/ST=Seoul/L=Seoul/O=Aegis/OU=IT Department/CN=pypi.aegis.local`""
        Invoke-Expression $opensslCmd
        Write-Success "SSL certificate generated"
    } catch {
        Write-Warning "OpenSSL not found. Please install OpenSSL or generate certificates manually."
        Write-Info "You can download OpenSSL from: https://slproweb.com/products/Win32OpenSSL.html"
    }
} else {
    Write-Info "SSL certificate already exists"
}

# htpasswd 파일 생성 (Docker 사용)
if (!(Test-Path "pypi-data\auth\.htpasswd")) {
    Write-Info "Creating authentication file..."
    
    $password = Read-Host "Please enter password for user '$Username'" -AsSecureString
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
    
    try {
        # Docker를 사용하여 htpasswd 실행
        $dockerCmd = "docker run --rm httpd:2.4-alpine htpasswd -nbB $Username $plainPassword"
        $htpasswdOutput = Invoke-Expression $dockerCmd
        $htpasswdOutput | Out-File -FilePath "pypi-data\auth\.htpasswd" -Encoding ASCII
        Write-Success "Authentication file created"
    } catch {
        Write-Warning "Docker not available. Creating basic auth file manually..."
        "$Username`:$plainPassword" | Out-File -FilePath "pypi-data\auth\.htpasswd" -Encoding ASCII
    }
} else {
    Write-Info "Authentication file already exists"
}

# Poetry repository 설정
Write-Info "Configuring Poetry repository..."

# Repository URL 설정
poetry config repositories.$RepositoryName "$PyPIServerURL/simple/"

# 인증 방식 선택
Write-Host ""
Write-Host "Choose authentication method:"
Write-Host "1) Username/Password"
Write-Host "2) API Token"
$authChoice = Read-Host "Enter choice (1 or 2)"

switch ($authChoice) {
    "1" {
        $password = Read-Host "Please enter password for user '$Username'" -AsSecureString
        $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
        poetry config http-basic.$RepositoryName $Username $plainPassword
        Write-Success "Username/password authentication configured"
    }
    "2" {
        $token = Read-Host "Please enter API token" -AsSecureString
        $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))
        poetry config pypi-token.$RepositoryName $plainToken
        Write-Success "Token authentication configured"
    }
    default {
        Write-Error "Invalid choice. Please run the script again."
        exit 1
    }
}

# Prometheus 설정 파일 생성
Write-Info "Creating monitoring configuration..."

$prometheusConfig = @"
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
"@

$prometheusConfig | Out-File -FilePath "monitoring\prometheus.yml" -Encoding UTF8

# Docker Compose 환경 변수 파일 생성
$envContent = @"
# Private PyPI Server Configuration
PYPI_SERVER_URL=$PyPIServerURL
PYPI_USERNAME=$Username
PYPI_REPOSITORY=$RepositoryName

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
"@

$envContent | Out-File -FilePath ".env.pypi" -Encoding UTF8

Write-Success "Configuration files created"

# 설정 확인
Write-Info "Verifying Poetry configuration..."
Write-Host ""
Write-Host "📋 Current Poetry configuration:"
poetry config --list | Select-String -Pattern "repositories|http-basic|pypi-token" | Select-String -Pattern $RepositoryName

# Docker Compose 파일 존재 확인
if (Test-Path "docker-compose.pypi.yml") {
    Write-Success "Docker Compose configuration found"
    
    Write-Host ""
    Write-Host "🐳 To start the Private PyPI server:"
    Write-Host "   docker-compose -f docker-compose.pypi.yml up -d"
    Write-Host ""
    Write-Host "🔍 To check server status:"
    Write-Host "   docker-compose -f docker-compose.pypi.yml ps"
    Write-Host ""
    Write-Host "📦 To deploy packages:"
    Write-Host "   python scripts/deploy-private.py --repository $RepositoryName"
    Write-Host ""
    Write-Host "🛑 To stop the server:"
    Write-Host "   docker-compose -f docker-compose.pypi.yml down"
} else {
    Write-Warning "Docker Compose configuration not found"
}

# 추가 설정 안내
Write-Host ""
Write-Host "📝 Additional setup steps:"
Write-Host "1. Add 'pypi.aegis.local' to your hosts file:"
Write-Host "   Add '127.0.0.1 pypi.aegis.local' to C:\Windows\System32\drivers\etc\hosts"
Write-Host ""
Write-Host "2. Configure pip to use the private repository:"
Write-Host "   pip config set global.extra-index-url $PyPIServerURL/simple/"
Write-Host "   pip config set global.trusted-host pypi.aegis.local"
Write-Host ""
Write-Host "3. Install packages from private repository:"
Write-Host "   pip install aegis-shared --extra-index-url $PyPIServerURL/simple/"

Write-Success "Private PyPI setup completed!"

# 테스트 연결 (선택적)
$testConnection = Read-Host "Do you want to test the connection? (y/n)"

if ($testConnection -eq "y" -or $testConnection -eq "Y") {
    Write-Info "Testing connection to $PyPIServerURL..."
    
    try {
        $response = Invoke-WebRequest -Uri "$PyPIServerURL/simple/" -UseBasicParsing -SkipCertificateCheck
        if ($response.StatusCode -eq 200) {
            Write-Success "Connection test successful!"
        } else {
            Write-Warning "Connection test failed with status: $($response.StatusCode)"
        }
    } catch {
        Write-Warning "Connection test failed. Make sure the server is running."
        Write-Info "Error: $($_.Exception.Message)"
    }
}