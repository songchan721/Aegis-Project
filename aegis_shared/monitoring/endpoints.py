from prometheus_client import make_asgi_app

def create_metrics_endpoint():
    return make_asgi_app()
