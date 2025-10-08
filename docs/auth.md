# 인증 및 인가 (Authentication & Authorization)

Aegis Shared Library의 인증 및 인가 모듈은 JWT 토큰 기반의 인증 시스템과 역할 기반 접근 제어(RBAC)를 제공합니다.

## 주요 구성 요소

### 1. JWT Handler

JWT 토큰의 생성, 검증, 갱신을 담당합니다.

```python
from aegis_shared.auth import JWTHandler
from datetime import timedelta

# JWT 핸들러 초기화
jwt_handler = JWTHandler(secret_key="your-secret-key")

# 액세스 토큰 생성
user_data = {
    "user_id": "user-123",
    "email": "user@example.com",
    "roles": ["user", "policy_reader"]
}

access_token = jwt_handler.create_access_token(
    data=user_data,
    expires_delta=timedelta(hours=1)
)

# 리프레시 토큰 생성
refresh_token = jwt_handler.create_refresh_token(
    data=user_data,
    expires_delta=timedelta(days=7)
)

# 서비스 토큰 생성 (서비스 간 통신용)
service_data = {
    "service_name": "policy-service",
    "permissions": ["read_policy", "write_policy"]
}

service_token = jwt_handler.create_service_token(
    data=service_data,
    expires_delta=timedelta(hours=24)
)

# 토큰 검증
try:
    payload = jwt_handler.verify_token(access_token)
    print(f"User ID: {payload['user_id']}")
    print(f"Roles: {payload['roles']}")
except TokenExpiredError:
    print("Token has expired")
except InvalidTokenError:
    print("Invalid token")
```

### 2. Authentication Middleware

FastAPI 애플리케이션에서 자동으로 토큰을 검증하는 미들웨어입니다.

```python
from fastapi import FastAPI
from aegis_shared.auth import AuthMiddleware, JWTHandler

app = FastAPI()

# JWT 핸들러 초기화
jwt_handler = JWTHandler(secret_key="your-secret-key")

# 인증 미들웨어 추가
auth_middleware = AuthMiddleware(jwt_handler=jwt_handler)
app.middleware("http")(auth_middleware)

# 보호된 엔드포인트
@app.get("/protected")
async def protected_endpoint(request: Request):
    # request.state.user에서 사용자 정보 접근 가능
    user_id = request.state.user_id
    user_data = request.state.user
    
    return {"message": f"Hello, {user_id}!"}
```

### 3. RBAC (Role-Based Access Control)

역할 기반 접근 제어 시스템입니다.

```python
from aegis_shared.auth.rbac import RBACManager, Permission, Role

# RBAC 매니저 초기화
rbac = RBACManager()

# 권한 정의
read_policy = Permission(
    name="read_policy",
    resource="policy",
    action="read"
)

write_policy = Permission(
    name="write_policy", 
    resource="policy",
    action="write"
)

# 역할 정의
policy_reader = Role(
    name="policy_reader",
    permissions=[read_policy]
)

policy_manager = Role(
    name="policy_manager",
    permissions=[read_policy, write_policy]
)

# 역할 등록
rbac.add_role(policy_reader)
rbac.add_role(policy_manager)

# 권한 확인
user_roles = ["policy_reader"]
can_read = rbac.check_permission(user_roles, "read_policy")  # True
can_write = rbac.check_permission(user_roles, "write_policy")  # False

# 데코레이터를 사용한 권한 확인
@rbac.require_permission("write_policy")
def create_policy(user_roles, policy_data):
    # 권한이 있는 경우에만 실행됨
    return create_new_policy(policy_data)

# 사용
try:
    result = create_policy(user_roles=["policy_manager"], policy_data={...})
except InsufficientPermissionsError:
    print("권한이 부족합니다")
```

### 4. FastAPI 의존성

FastAPI에서 사용할 수 있는 의존성 함수들입니다.

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from aegis_shared.auth import JWTHandler

security = HTTPBearer()
jwt_handler = JWTHandler(secret_key="your-secret-key")

async def get_current_user(token: str = Depends(security)):
    """현재 사용자 정보를 추출하는 의존성"""
    try:
        payload = jwt_handler.verify_token(token.credentials)
        return payload
    except (TokenExpiredError, InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_roles(required_roles: list):
    """특정 역할을 요구하는 의존성 팩토리"""
    def check_roles(current_user: dict = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return check_roles

# 사용 예시
@app.get("/admin")
async def admin_endpoint(
    current_user: dict = Depends(require_roles(["admin"]))
):
    return {"message": "Admin access granted"}
```

## 설정

### 환경 변수

```bash
# JWT 설정
JWT_SECRET=your-super-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 서비스 토큰 설정
SERVICE_TOKEN_EXPIRATION_HOURS=168  # 7일
```

### 설정 클래스

```python
from aegis_shared.config import Settings

settings = Settings()

jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret,
    algorithm=settings.jwt_algorithm
)
```

## 보안 고려사항

### 1. 시크릿 키 관리

```python
# ❌ 하드코딩하지 마세요
jwt_handler = JWTHandler(secret_key="hardcoded-secret")

# ✅ 환경 변수나 시크릿 관리 시스템 사용
jwt_handler = JWTHandler(secret_key=os.getenv("JWT_SECRET"))
```

### 2. 토큰 만료 시간

```python
# 액세스 토큰: 짧은 만료 시간 (15분 - 1시간)
access_token = jwt_handler.create_access_token(
    data=user_data,
    expires_delta=timedelta(minutes=30)
)

# 리프레시 토큰: 긴 만료 시간 (7일 - 30일)
refresh_token = jwt_handler.create_refresh_token(
    data=user_data,
    expires_delta=timedelta(days=7)
)
```

### 3. 토큰 블랙리스트

```python
# Redis를 사용한 토큰 블랙리스트 구현 예시
from aegis_shared.cache import CacheClient

class TokenBlacklist:
    def __init__(self, cache_client: CacheClient):
        self.cache = cache_client
    
    async def blacklist_token(self, token: str, expires_in: int):
        """토큰을 블랙리스트에 추가"""
        await self.cache.set(f"blacklist:{token}", "1", ttl=expires_in)
    
    async def is_blacklisted(self, token: str) -> bool:
        """토큰이 블랙리스트에 있는지 확인"""
        result = await self.cache.get(f"blacklist:{token}")
        return result is not None
```

## 에러 처리

```python
from aegis_shared.errors.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    InsufficientPermissionsError
)

try:
    payload = jwt_handler.verify_token(token)
except TokenExpiredError:
    # 토큰 만료 처리
    return {"error": "Token expired", "code": "TOKEN_EXPIRED"}
except InvalidTokenError:
    # 유효하지 않은 토큰 처리
    return {"error": "Invalid token", "code": "INVALID_TOKEN"}
except InsufficientPermissionsError as e:
    # 권한 부족 처리
    return {
        "error": "Insufficient permissions",
        "code": "INSUFFICIENT_PERMISSIONS",
        "required_permission": e.details.get("required_permission")
    }
```

## 테스트

```python
import pytest
from aegis_shared.auth import JWTHandler
from aegis_shared.errors.exceptions import TokenExpiredError

def test_jwt_token_creation():
    jwt_handler = JWTHandler(secret_key="test-secret")
    
    user_data = {"user_id": "test-user", "email": "test@example.com"}
    token = jwt_handler.create_access_token(user_data)
    
    assert token is not None
    
    payload = jwt_handler.verify_token(token)
    assert payload["user_id"] == "test-user"
    assert payload["email"] == "test@example.com"

def test_expired_token():
    jwt_handler = JWTHandler(secret_key="test-secret")
    
    # 이미 만료된 토큰 생성
    from datetime import timedelta
    expired_token = jwt_handler.create_access_token(
        {"user_id": "test"},
        expires_delta=timedelta(seconds=-1)
    )
    
    with pytest.raises(TokenExpiredError):
        jwt_handler.verify_token(expired_token)
```

## 모범 사례

1. **시크릿 키는 충분히 복잡하게**: 최소 32자 이상의 랜덤 문자열 사용
2. **적절한 만료 시간 설정**: 액세스 토큰은 짧게, 리프레시 토큰은 길게
3. **HTTPS 사용**: 토큰 전송 시 반드시 HTTPS 사용
4. **토큰 저장 주의**: 클라이언트에서 안전한 저장소 사용
5. **권한 최소화**: 필요한 최소한의 권한만 부여
6. **정기적인 토큰 갱신**: 리프레시 토큰을 사용한 정기적인 토큰 갱신