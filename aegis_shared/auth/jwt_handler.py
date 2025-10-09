"""
JWT 토큰 처리기

JWT 토큰 생성 및 검증 기능을 제공합니다.
"""

from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional
import jwt

class TokenExpiredError(Exception):
    """토큰 만료 예외"""
    pass

class InvalidTokenError(Exception):
    """유효하지 않은 토큰 예외"""
    pass

class JWTHandler:
    """JWT 토큰 생성 및 검증"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        JWT 핸들러 초기화
        
        Args:
            secret_key: JWT 서명용 비밀 키
            algorithm: JWT 알고리즘 (기본값: HS256)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        액세스 토큰 생성
        
        Args:
            data: 토큰에 포함할 데이터
            expires_delta: 만료 시간 (기본값: 30분)
            
        Returns:
            JWT 토큰 문자열
        """
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
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        리프레시 토큰 생성
        
        Args:
            data: 토큰에 포함할 데이터
            expires_delta: 만료 시간 (기본값: 7일)
            
        Returns:
            JWT 토큰 문자열
        """
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
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        토큰 검증
        
        Args:
            token: 검증할 JWT 토큰
            
        Returns:
            토큰 페이로드
            
        Raises:
            TokenExpiredError: 토큰이 만료된 경우
            InvalidTokenError: 토큰이 유효하지 않은 경우
        """
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