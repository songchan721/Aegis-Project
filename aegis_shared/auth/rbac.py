"""
Role-Based Access Control (RBAC) implementation.
"""

from dataclasses import dataclass
from functools import wraps
from typing import Dict, List, Set

from fastapi import HTTPException, Request

from aegis_shared.errors.exceptions import InsufficientPermissionsError


@dataclass
class Permission:
    """Permission definition."""

    name: str
    resource: str
    action: str

    def __str__(self):
        return f"{self.resource}:{self.action}"


@dataclass
class Role:
    """Role definition with permissions."""

    name: str
    permissions: List[Permission]

    def has_permission(self, permission_name: str) -> bool:
        """Check if role has specific permission."""
        return any(p.name == permission_name for p in self.permissions)


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}

    def add_role(self, role: Role) -> None:
        """Add a role to the system."""
        self.roles[role.name] = role

        # Add permissions to permission registry
        for permission in role.permissions:
            self.permissions[permission.name] = permission

    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the system."""
        self.permissions[permission.name] = permission

    def check_permission(self, user_roles: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and role.has_permission(required_permission):
                return True
        return False

    def get_user_permissions(self, user_roles: List[str]) -> Set[str]:
        """Get all permissions for user roles."""
        permissions = set()
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role:
                permissions.update(p.name for p in role.permissions)
        return permissions

    def require_permission(self, required_permission: str):
        """Decorator to require specific permission."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user_roles from kwargs or args
                user_roles = kwargs.get("user_roles", [])
                if not user_roles and args:
                    # Try to find user_roles in args
                    for arg in args:
                        if isinstance(arg, list) and all(
                            isinstance(item, str) for item in arg
                        ):
                            user_roles = arg
                            break

                if not self.check_permission(user_roles, required_permission):
                    raise InsufficientPermissionsError(
                        f"Permission '{required_permission}' required",
                        required_permission=required_permission,
                        user_roles=user_roles,
                    )

                return func(*args, **kwargs)

            return wrapper

        return decorator


def require_role(required_roles: List[str]):
    """Decorator to require specific roles."""

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # This is a simplified example. In a real application, you would
            # fetch the user's roles from the database or a user service.
            user_roles = (
                request.state.user.get("roles", [])
                if hasattr(request.state, "user")
                else []
            )

            if not any(role in user_roles for role in required_roles):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
