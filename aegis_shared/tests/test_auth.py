"""
Tests for authentication module.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import jwt as pyjwt

from aegis_shared.auth.jwt import JWTHandler
from aegis_shared.auth.middleware import AuthMiddleware
from aegis_shared.auth.rbac import RBACManager, Permission, Role
from aegis_shared.errors.exceptions import (
    TokenExpiredError, 
    InvalidTokenError, 
    InsufficientPermissionsError
)


class TestJWTHandler:
    """Test JWT token handling."""
    
    @pytest.fixture
    def jwt_handler(self, sample_jwt_secret):
        return JWTHandler(secret_key=sample_jwt_secret)
    
    def test_create_access_token(self, jwt_handler, sample_user_payload):
        """Test access token creation."""
        token = jwt_handler.create_access_token(sample_user_payload)
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token can be decoded
        payload = jwt_handler.verify_token(token)
        assert payload["user_id"] == sample_user_payload["user_id"]
        assert payload["email"] == sample_user_payload["email"]
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self, jwt_handler, sample_user_payload):
        """Test refresh token creation."""
        token = jwt_handler.create_refresh_token(sample_user_payload)
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token can be decoded
        payload = jwt_handler.verify_token(token)
        assert payload["user_id"] == sample_user_payload["user_id"]
        assert payload["type"] == "refresh"
    
    def test_create_token_with_custom_expiry(self, jwt_handler, sample_user_payload):
        """Test token creation with custom expiry."""
        expires_delta = timedelta(minutes=5)
        token = jwt_handler.create_access_token(
            sample_user_payload, 
            expires_delta=expires_delta
        )
        
        payload = jwt_handler.verify_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        
        # Check that expiry is approximately 5 minutes from issued time
        assert (exp_time - iat_time).total_seconds() == pytest.approx(300, abs=5)
    
    def test_verify_valid_token(self, jwt_handler, sample_user_payload):
        """Test verification of valid token."""
        token = jwt_handler.create_access_token(sample_user_payload)
        payload = jwt_handler.verify_token(token)
        
        assert payload["user_id"] == sample_user_payload["user_id"]
        assert payload["email"] == sample_user_payload["email"]
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_expired_token(self, jwt_handler, sample_user_payload):
        """Test verification of expired token."""
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = jwt_handler.create_access_token(
            sample_user_payload, 
            expires_delta=expires_delta
        )
        
        with pytest.raises(TokenExpiredError):
            jwt_handler.verify_token(token)
    
    def test_verify_invalid_token(self, jwt_handler):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(InvalidTokenError):
            jwt_handler.verify_token(invalid_token)
    
    def test_verify_token_wrong_secret(self, sample_user_payload):
        """Test verification with wrong secret."""
        handler1 = JWTHandler(secret_key="secret1")
        handler2 = JWTHandler(secret_key="secret2")
        
        token = handler1.create_access_token(sample_user_payload)
        
        with pytest.raises(InvalidTokenError):
            handler2.verify_token(token)


class TestAuthMiddleware:
    """Test authentication middleware."""
    
    @pytest.fixture
    def auth_middleware(self, sample_jwt_secret):
        jwt_handler = JWTHandler(secret_key=sample_jwt_secret)
        return AuthMiddleware(jwt_handler=jwt_handler)
    
    @pytest.mark.asyncio
    async def test_middleware_with_valid_token(self, auth_middleware, sample_user_payload):
        """Test middleware with valid token."""
        # Create mock request and response
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.state = Mock()
        
        # Create valid token
        token = auth_middleware.jwt_handler.create_access_token(sample_user_payload)
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        # Mock call_next
        async def mock_call_next(request):
            return Mock()  # Mock response
        
        # Execute middleware
        response = await auth_middleware(mock_request, mock_call_next)
        
        # Verify user info was set
        assert hasattr(mock_request.state, 'user')
        assert mock_request.state.user_id == sample_user_payload["user_id"]
    
    @pytest.mark.asyncio
    async def test_middleware_without_token(self, auth_middleware):
        """Test middleware without token."""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.state = Mock()
        
        # Mock state가 user 속성을 가지지 않도록 설정
        del mock_request.state.user
        
        async def mock_call_next(request):
            return Mock()
        
        response = await auth_middleware(mock_request, mock_call_next)
        
        # Should not set user info
        with pytest.raises(AttributeError):
            _ = mock_request.state.user
    
    @pytest.mark.asyncio
    async def test_middleware_with_invalid_token(self, auth_middleware):
        """Test middleware with invalid token."""
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer invalid.token"}
        mock_request.state = Mock()
        
        # Mock state가 user 속성을 가지지 않도록 설정
        del mock_request.state.user
        
        async def mock_call_next(request):
            return Mock()
        
        response = await auth_middleware(mock_request, mock_call_next)
        
        # Should not set user info (invalid token should not set user)
        with pytest.raises(AttributeError):
            _ = mock_request.state.user


class TestRBACManager:
    """Test Role-Based Access Control."""
    
    @pytest.fixture
    def rbac_manager(self):
        return RBACManager()
    
    def test_create_permission(self, rbac_manager):
        """Test permission creation."""
        permission = Permission(
            name="read_policy",
            resource="policy",
            action="read"
        )
        
        assert permission.name == "read_policy"
        assert permission.resource == "policy"
        assert permission.action == "read"
    
    def test_create_role(self, rbac_manager):
        """Test role creation."""
        permissions = [
            Permission("read_policy", "policy", "read"),
            Permission("write_policy", "policy", "write")
        ]
        
        role = Role(
            name="policy_manager",
            permissions=permissions
        )
        
        assert role.name == "policy_manager"
        assert len(role.permissions) == 2
    
    def test_check_permission_success(self, rbac_manager):
        """Test successful permission check."""
        permissions = [
            Permission("read_policy", "policy", "read")
        ]
        
        user_roles = ["policy_reader"]
        rbac_manager.roles["policy_reader"] = Role("policy_reader", permissions)
        
        result = rbac_manager.check_permission(
            user_roles=user_roles,
            required_permission="read_policy"
        )
        
        assert result is True
    
    def test_check_permission_failure(self, rbac_manager):
        """Test failed permission check."""
        permissions = [
            Permission("read_policy", "policy", "read")
        ]
        
        user_roles = ["policy_reader"]
        rbac_manager.roles["policy_reader"] = Role("policy_reader", permissions)
        
        result = rbac_manager.check_permission(
            user_roles=user_roles,
            required_permission="write_policy"
        )
        
        assert result is False
    
    def test_require_permission_decorator_success(self, rbac_manager):
        """Test permission decorator with success."""
        permissions = [
            Permission("read_policy", "policy", "read")
        ]
        
        rbac_manager.roles["admin"] = Role("admin", permissions)
        
        @rbac_manager.require_permission("read_policy")
        def protected_function(user_roles):
            return "success"
        
        result = protected_function(user_roles=["admin"])
        assert result == "success"
    
    def test_require_permission_decorator_failure(self, rbac_manager):
        """Test permission decorator with failure."""
        permissions = [
            Permission("read_policy", "policy", "read")
        ]
        
        rbac_manager.roles["user"] = Role("user", permissions)
        
        @rbac_manager.require_permission("write_policy")
        def protected_function(user_roles):
            return "success"
        
        with pytest.raises(InsufficientPermissionsError):
            protected_function(user_roles=["user"])


class TestServiceAccount:
    """Test service account functionality."""
    
    def test_service_account_token_creation(self, sample_jwt_secret):
        """Test service account token creation."""
        jwt_handler = JWTHandler(secret_key=sample_jwt_secret)
        
        service_data = {
            "service_name": "policy-service",
            "permissions": ["read_policy", "write_policy"]
        }
        
        token = jwt_handler.create_service_token(service_data)
        assert token is not None
        
        payload = jwt_handler.verify_token(token)
        assert payload["service_name"] == "policy-service"
        assert payload["type"] == "service"
    
    def test_service_account_verification(self, sample_jwt_secret):
        """Test service account token verification."""
        jwt_handler = JWTHandler(secret_key=sample_jwt_secret)
        
        service_data = {
            "service_name": "user-service",
            "permissions": ["read_user"]
        }
        
        token = jwt_handler.create_service_token(service_data)
        payload = jwt_handler.verify_token(token)
        
        assert jwt_handler.is_service_token(payload)
        assert payload["service_name"] == "user-service"
