"""
Aegis Shared Library - 인증 모듈

JWT 토큰 처리 및 인증 미들웨어를 제공합니다.
"""

from aegis_shared.auth.dependencies import create_get_current_user, get_current_user
from aegis_shared.auth.jwt import JWTHandler
from aegis_shared.auth.middleware import AuthMiddleware
from aegis_shared.auth.rbac import Permission, RBACManager, Role, require_role

__all__ = [
    "JWTHandler",
    "AuthMiddleware",
    "get_current_user",
    "create_get_current_user",
    "Permission",
    "Role",
    "RBACManager",
    "require_role",
]
