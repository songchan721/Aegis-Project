import os

os.environ["ENVIRONMENT"] = "test"


def test_settings():
    # This requires environment variables to be set, so it's more of an
    # integration test.
    pass
