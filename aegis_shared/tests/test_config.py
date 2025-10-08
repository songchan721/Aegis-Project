import pytest
import os
os.environ["ENVIRONMENT"] = "test"
from ..config.loader import Settings

def test_settings():
    # This requires environment variables to be set, so it's more of an integration test.
    pass
