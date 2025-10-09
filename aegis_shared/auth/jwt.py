"""
JWT token handling for authentication.
"""
import jwt
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

from aegis_shared.errors.exceptions import TokenExpiredError, InvalidTokenError


class JWTHandler:
    """JWT token handler for creating and verifying tokens."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, identity: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token for backward compatibility."""
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=15)
        to_encode = {"exp": expire, "sub": str(identity)}
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create an access token with custom data."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=30)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a refresh token with custom data."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(days=7)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_service_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a service token for service-to-service communication."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(hours=1)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "service"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[str]:
        """Decode token for backward compatibility."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload["sub"]
        except jwt.PyJWTError:
            return None

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Invalid token")

    def is_service_token(self, payload: Dict[str, Any]) -> bool:
        """Check if the token payload represents a service token."""
        return payload.get("type") == "service"

    def refresh_token(self, token: str, expires_delta: Optional[timedelta] = None) -> Optional[str]:
        """Refresh a token (backward compatibility)."""
        identity = self.decode_token(token)
        if identity:
            return self.create_token(identity, expires_delta)
        return None
