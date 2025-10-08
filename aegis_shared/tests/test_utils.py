import pytest
from ..utils.time import utcnow
from ..utils.string import to_slug
from ..utils.crypto import hash_password, check_password
from ..utils.validation import is_email

def test_time_utils():
    assert utcnow() is not None

def test_string_utils():
    assert to_slug("Hello World") == "hello-world"

def test_crypto_utils():
    password = "password"
    hashed = hash_password(password)
    assert check_password(password, hashed)

def test_validation_utils():
    assert is_email("test@test.com")
    assert not is_email("test")
