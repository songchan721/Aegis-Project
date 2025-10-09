"""
인증 미들웨어

FastAPI 인증 미들웨어를 제공합니다.
"""

from typing import Callable

from aegis_shared.auth.jwt_handler import JWTHandler
from aegis_shared.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware:
    """인증 미들웨어"""

    def __init__(self, jwt_handler: JWTHandler):
        """
        인증 미들웨어 초기화

        Args:
            jwt_handler: JWT 핸들러 인스턴스
        """
        self.jwt_handler = jwt_handler

    async def __call__(self, request, call_next: Callable):
        """
        미들웨어 실행

        Args:
            request: FastAPI Request 객체
            call_next: 다음 미들웨어 또는 엔드포인트

        Returns:
            Response 객체
        """
        # Authorization 헤더 확인
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = self.jwt_handler.verify_token(token)
                request.state.user = payload
                request.state.user_id = payload.get("user_id")

                # 로깅 컨텍스트에 사용자 정보 추가
                from aegis_shared.logging import add_context

                add_context(user_id=payload.get("user_id"))

            except Exception as e:
                logger.warning(f"Token verification failed: {e}")

        response = await call_next(request)
        return response
