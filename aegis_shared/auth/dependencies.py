"""
인증 의존성 함수들

FastAPI 의존성으로 사용할 수 있는 인증 관련 함수들을 제공합니다.
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aegis_shared.auth.jwt import JWTHandler
from aegis_shared.errors.exceptions import InvalidTokenError, TokenExpiredError

security = HTTPBearer()


def create_get_current_user(jwt_handler: JWTHandler):
    """
    현재 사용자 정보를 추출하는 의존성 함수를 생성합니다.

    Args:
        jwt_handler: JWT 핸들러 인스턴스

    Returns:
        FastAPI 의존성 함수
    """

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> Dict[str, Any]:
        """
        현재 사용자 정보 추출

        Args:
            credentials: HTTP Bearer 토큰

        Returns:
            사용자 정보 딕셔너리

        Raises:
            HTTPException: 토큰이 유효하지 않은 경우
        """
        try:
            payload = jwt_handler.verify_token(credentials.credentials)
            return payload
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return get_current_user


# 기본 get_current_user 함수 (JWT 핸들러가 필요함)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    기본 현재 사용자 정보 추출 함수

    주의: 이 함수를 사용하려면 JWT 핸들러가 전역적으로 설정되어 있어야 합니다.
    일반적으로는 create_get_current_user를 사용하는 것이 좋습니다.
    """
    # 이 함수는 실제로는 JWT 핸들러가 필요하므로
    # 실제 구현에서는 create_get_current_user를 사용해야 합니다.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="JWT handler not configured. Use create_get_current_user instead.",
    )
