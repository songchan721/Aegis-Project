import sentry_sdk

def initialize_sentry(dsn: str, environment: str, release: str):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
    )

def capture_exception(exc: Exception):
    sentry_sdk.capture_exception(exc)
