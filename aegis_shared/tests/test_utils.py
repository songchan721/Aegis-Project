"""
Comprehensive tests for aegis_shared utils module.

Tests cover:
- Time utilities (parsing, formatting, timezone conversion)
- String utilities (slug generation, normalization)
- Crypto utilities (hashing, encryption, decryption)
- File utilities (MIME type detection, validation)
- Validation utilities (email, phone, password)
- Pagination utilities (offset calculation, parameter validation)
"""

import os
import tempfile
from datetime import datetime

import pytest
import pytz

from aegis_shared.models.pagination import PaginatedResponse
from aegis_shared.utils.crypto import (
    check_password,
    decrypt,
    encrypt,
    generate_key,
    hash_password,
)
from aegis_shared.utils.files import get_mime_type, is_allowed_file_type
from aegis_shared.utils.pagination import (
    calculate_offset,
    calculate_total_pages,
    paginate,
    validate_pagination_params,
)
from aegis_shared.utils.string import to_slug
from aegis_shared.utils.time import format_datetime, parse_datetime, to_utc, utcnow
from aegis_shared.utils.validation import is_email, is_phone_number, is_strong_password

# ==================== Time Utilities Tests ====================


class TestTimeUtils:
    """Test time utility functions."""

    def test_utcnow_returns_utc_datetime(self):
        """Test that utcnow returns a timezone-aware UTC datetime."""
        now = utcnow()
        assert now.tzinfo is not None
        assert now.tzinfo == pytz.utc

    def test_to_utc_naive_datetime(self):
        """Test converting naive datetime to UTC."""
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)
        utc_dt = to_utc(naive_dt)
        assert utc_dt.tzinfo == pytz.utc

    def test_to_utc_aware_datetime(self):
        """Test converting timezone-aware datetime to UTC."""
        eastern = pytz.timezone("US/Eastern")
        eastern_dt = eastern.localize(datetime(2024, 1, 15, 12, 0, 0))
        utc_dt = to_utc(eastern_dt)
        assert utc_dt.tzinfo == pytz.utc
        # Eastern time is UTC-5 (or UTC-4 during DST)
        # So 12:00 EST/EDT should be 17:00 or 16:00 UTC
        assert utc_dt.hour in [16, 17]

    def test_format_datetime_default_format(self):
        """Test formatting datetime with default format."""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        formatted = format_datetime(dt)
        assert formatted == "2024-01-15 12:30:45"

    def test_format_datetime_custom_format(self):
        """Test formatting datetime with custom format."""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        formatted = format_datetime(dt, "%Y/%m/%d")
        assert formatted == "2024/01/15"

    def test_parse_datetime_default_format(self):
        """Test parsing datetime string with default format."""
        dt_str = "2024-01-15 12:30:45"
        dt = parse_datetime(dt_str)
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_parse_datetime_custom_format(self):
        """Test parsing datetime string with custom format."""
        dt_str = "2024/01/15"
        dt = parse_datetime(dt_str, "%Y/%m/%d")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15


# ==================== String Utilities Tests ====================


class TestStringUtils:
    """Test string utility functions."""

    def test_to_slug_basic(self):
        """Test basic slug generation."""
        assert to_slug("Hello World") == "hello-world"

    def test_to_slug_with_spaces(self):
        """Test slug generation with multiple spaces."""
        assert to_slug("Hello   World") == "hello-world"

    def test_to_slug_with_special_chars(self):
        """Test slug generation removes special characters but keeps spaces
        as dashes."""
        assert to_slug("Hello, World!") == "hello-world"

    def test_to_slug_with_underscores(self):
        """Test slug generation converts underscores to dashes."""
        assert to_slug("hello_world_test") == "hello-world-test"

    def test_to_slug_with_mixed_case(self):
        """Test slug generation converts to lowercase."""
        assert to_slug("HeLLo WoRLd") == "hello-world"

    def test_to_slug_with_leading_trailing_spaces(self):
        """Test slug generation strips leading/trailing spaces."""
        assert to_slug("  hello world  ") == "hello-world"

    def test_to_slug_with_numbers(self):
        """Test slug generation preserves numbers."""
        assert to_slug("Test 123 ABC") == "test-123-abc"

    def test_to_slug_empty_string(self):
        """Test slug generation with empty string."""
        assert to_slug("") == ""


# ==================== Crypto Utilities Tests ====================


class TestCryptoUtils:
    """Test cryptography utility functions."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        hashed = hash_password("password123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_each_time(self):
        """Test that hashing the same password produces different results
        (due to salt)."""
        password = "password123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts

    def test_check_password_correct(self):
        """Test password verification with correct password."""
        password = "password123"
        hashed = hash_password(password)
        assert check_password(password, hashed) is True

    def test_check_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "password123"
        hashed = hash_password(password)
        assert check_password("wrongpassword", hashed) is False

    def test_generate_key_returns_bytes(self):
        """Test that generate_key returns bytes."""
        key = generate_key()
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_generate_key_unique(self):
        """Test that generate_key produces unique keys."""
        key1 = generate_key()
        key2 = generate_key()
        assert key1 != key2

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work together."""
        key = generate_key()
        original_data = b"sensitive information"
        encrypted = encrypt(original_data, key)
        decrypted = decrypt(encrypted, key)
        assert decrypted == original_data

    def test_encrypt_returns_different_data(self):
        """Test that encrypted data is different from original."""
        key = generate_key()
        original_data = b"sensitive information"
        encrypted = encrypt(original_data, key)
        assert encrypted != original_data

    def test_decrypt_with_wrong_key_fails(self):
        """Test that decryption with wrong key fails."""
        key1 = generate_key()
        key2 = generate_key()
        original_data = b"sensitive information"
        encrypted = encrypt(original_data, key1)

        with pytest.raises(Exception):  # Fernet raises InvalidToken
            decrypt(encrypted, key2)


# ==================== File Utilities Tests ====================


class TestFileUtils:
    """Test file utility functions."""

    def test_get_mime_type_text_file(self):
        """Test MIME type detection for text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, world!")
            temp_path = f.name

        try:
            mime_type = get_mime_type(temp_path)
            assert mime_type.startswith("text/")
        finally:
            os.unlink(temp_path)

    def test_get_mime_type_json_file(self):
        """Test MIME type detection for JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value"}')
            temp_path = f.name

        try:
            mime_type = get_mime_type(temp_path)
            # Could be application/json or text/plain depending on magic
            assert "json" in mime_type or "text" in mime_type
        finally:
            os.unlink(temp_path)

    def test_is_allowed_file_type_allowed(self):
        """Test file type validation with allowed type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, world!")
            temp_path = f.name

        try:
            mime_type = get_mime_type(temp_path)
            allowed_types = [mime_type, "application/pdf"]
            assert is_allowed_file_type(temp_path, allowed_types) is True
        finally:
            os.unlink(temp_path)

    def test_is_allowed_file_type_not_allowed(self):
        """Test file type validation with disallowed type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, world!")
            temp_path = f.name

        try:
            allowed_types = ["application/pdf", "image/jpeg"]
            assert is_allowed_file_type(temp_path, allowed_types) is False
        finally:
            os.unlink(temp_path)


# ==================== Validation Utilities Tests ====================


class TestValidationUtils:
    """Test validation utility functions."""

    # Email validation tests
    def test_is_email_valid_simple(self):
        """Test valid simple email."""
        assert is_email("test@test.com") is True

    def test_is_email_valid_with_subdomain(self):
        """Test valid email with subdomain."""
        assert is_email("user@mail.example.com") is True

    def test_is_email_valid_with_plus(self):
        """Test valid email with plus sign."""
        assert is_email("user+tag@example.com") is True

    def test_is_email_invalid_no_at(self):
        """Test invalid email without @ symbol."""
        assert is_email("testtest.com") is False

    def test_is_email_invalid_no_domain(self):
        """Test invalid email without domain."""
        assert is_email("test@") is False

    def test_is_email_invalid_empty(self):
        """Test invalid empty email."""
        assert is_email("") is False

    # Phone number validation tests
    def test_is_phone_number_valid_10_digits(self):
        """Test valid 10-digit phone number."""
        assert is_phone_number("1234567890") is True

    def test_is_phone_number_valid_with_plus(self):
        """Test valid phone number with + prefix."""
        assert is_phone_number("+821012345678") is True

    def test_is_phone_number_valid_15_digits(self):
        """Test valid 15-digit phone number (max)."""
        assert is_phone_number("123456789012345") is True

    def test_is_phone_number_invalid_too_short(self):
        """Test invalid phone number (too short)."""
        assert is_phone_number("123456789") is False

    def test_is_phone_number_invalid_too_long(self):
        """Test invalid phone number (too long)."""
        assert is_phone_number("1234567890123456") is False

    def test_is_phone_number_invalid_with_letters(self):
        """Test invalid phone number with letters."""
        assert is_phone_number("123abc7890") is False

    def test_is_phone_number_invalid_with_spaces(self):
        """Test invalid phone number with spaces."""
        assert is_phone_number("123 456 7890") is False

    # Password strength validation tests
    def test_is_strong_password_valid(self):
        """Test valid strong password."""
        assert is_strong_password("Password123") is True

    def test_is_strong_password_valid_complex(self):
        """Test valid complex strong password."""
        assert is_strong_password("MyP@ssw0rd!") is True

    def test_is_strong_password_invalid_too_short(self):
        """Test invalid password (too short)."""
        assert is_strong_password("Pass1") is False

    def test_is_strong_password_invalid_no_uppercase(self):
        """Test invalid password (no uppercase)."""
        assert is_strong_password("password123") is False

    def test_is_strong_password_invalid_no_lowercase(self):
        """Test invalid password (no lowercase)."""
        assert is_strong_password("PASSWORD123") is False

    def test_is_strong_password_invalid_no_digit(self):
        """Test invalid password (no digit)."""
        assert is_strong_password("PasswordABC") is False

    def test_is_strong_password_invalid_empty(self):
        """Test invalid empty password."""
        assert is_strong_password("") is False


# ==================== Pagination Utilities Tests ====================


class TestPaginationUtils:
    """Test pagination utility functions."""

    def test_calculate_offset_page_1(self):
        """Test offset calculation for first page."""
        offset = calculate_offset(page=1, page_size=10)
        assert offset == 0

    def test_calculate_offset_page_2(self):
        """Test offset calculation for second page."""
        offset = calculate_offset(page=2, page_size=10)
        assert offset == 10

    def test_calculate_offset_page_5(self):
        """Test offset calculation for fifth page."""
        offset = calculate_offset(page=5, page_size=20)
        assert offset == 80

    def test_calculate_offset_invalid_page(self):
        """Test offset calculation with invalid page number."""
        offset = calculate_offset(page=0, page_size=10)
        assert offset == 0  # Should default to page 1

    def test_calculate_total_pages_exact(self):
        """Test total pages calculation with exact division."""
        total_pages = calculate_total_pages(total=100, page_size=10)
        assert total_pages == 10

    def test_calculate_total_pages_with_remainder(self):
        """Test total pages calculation with remainder."""
        total_pages = calculate_total_pages(total=105, page_size=10)
        assert total_pages == 11

    def test_calculate_total_pages_zero_items(self):
        """Test total pages calculation with zero items."""
        total_pages = calculate_total_pages(total=0, page_size=10)
        assert total_pages == 0

    def test_calculate_total_pages_invalid_page_size(self):
        """Test total pages calculation with invalid page size."""
        total_pages = calculate_total_pages(total=100, page_size=0)
        assert total_pages == 0

    def test_paginate_basic(self):
        """Test basic pagination."""
        items = [1, 2, 3, 4, 5]
        result = paginate(items=items, total=100, page=1, page_size=5)

        assert isinstance(result, PaginatedResponse)
        assert result.items == items
        assert result.total == 100
        assert result.page == 1
        assert result.page_size == 5
        assert result.total_pages == 20

    def test_paginate_last_page_partial(self):
        """Test pagination for last page with partial items."""
        items = [96, 97, 98]
        result = paginate(items=items, total=98, page=10, page_size=10)

        assert result.items == items
        assert result.total == 98
        assert result.page == 10
        assert result.page_size == 10
        assert result.total_pages == 10

    def test_paginate_empty_items(self):
        """Test pagination with empty items."""
        items = []
        result = paginate(items=items, total=0, page=1, page_size=10)

        assert result.items == []
        assert result.total == 0
        assert result.total_pages == 0

    def test_validate_pagination_params_valid(self):
        """Test validation with valid parameters."""
        page, page_size = validate_pagination_params(page=2, page_size=20)
        assert page == 2
        assert page_size == 20

    def test_validate_pagination_params_negative_page(self):
        """Test validation with negative page number."""
        page, page_size = validate_pagination_params(page=-1, page_size=10)
        assert page == 1  # Should be normalized to 1
        assert page_size == 10

    def test_validate_pagination_params_zero_page(self):
        """Test validation with zero page number."""
        page, page_size = validate_pagination_params(page=0, page_size=10)
        assert page == 1  # Should be normalized to 1

    def test_validate_pagination_params_exceeds_max(self):
        """Test validation with page size exceeding max."""
        page, page_size = validate_pagination_params(
            page=1, page_size=200, max_page_size=100
        )
        assert page == 1
        assert page_size == 100  # Should be capped at max

    def test_validate_pagination_params_negative_page_size(self):
        """Test validation with negative page size."""
        page, page_size = validate_pagination_params(page=1, page_size=-10)
        assert page_size == 1  # Should be normalized to 1

    def test_validate_pagination_params_custom_max(self):
        """Test validation with custom max page size."""
        page, page_size = validate_pagination_params(
            page=1, page_size=50, max_page_size=25
        )
        assert page_size == 25  # Should be capped at custom max


# ==================== Integration Tests ====================


def test_utils_integration():
    """Integration test combining multiple utilities."""
    # 1. Time utilities
    now = utcnow()
    formatted_time = format_datetime(now, "%Y-%m-%d")

    # 2. String utilities
    slug = to_slug(f"Event {formatted_time}")
    assert "event" in slug
    assert "-" in slug

    # 3. Crypto utilities
    password = "StrongPassword123"
    assert is_strong_password(password)

    hashed = hash_password(password)
    assert check_password(password, hashed)

    # 4. Validation utilities
    email = "user@example.com"
    assert is_email(email)

    # 5. Encryption
    key = generate_key()
    sensitive_data = email.encode("utf-8")
    encrypted = encrypt(sensitive_data, key)
    decrypted = decrypt(encrypted, key)
    assert decrypted.decode("utf-8") == email

    # 6. Pagination utilities
    page, page_size = validate_pagination_params(page=1, page_size=10)
    offset = calculate_offset(page, page_size)
    items = list(range(offset, offset + page_size))
    paginated = paginate(items, total=100, page=page, page_size=page_size)
    assert paginated.total_pages == 10
    assert len(paginated.items) == 10
