from datetime import UTC, datetime

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, make_asgi_app
from starlette.responses import Response


def create_metrics_endpoint():
    """메트릭 및 헬스 체크 엔드포인트를 가진 FastAPI 앱 생성"""
    app = FastAPI(title="Monitoring Endpoints")

    # Prometheus 메트릭 앱
    make_asgi_app()

    @app.get("/metrics")
    async def metrics():
        """Prometheus 메트릭 엔드포인트"""
        from prometheus_client import generate_latest

        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    @app.get("/health")
    async def health():
        """헬스 체크 엔드포인트"""
        return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}

    return app
