import json

from pydantic import BaseModel

from ..models.base import BaseEntity
from ..models.contracts import UserProfile
from ..models.enums import UserRole
from ..models.masking import (
    MaskedCreditCard,
    MaskedEmail,
    MaskedPassword,
    MaskedPhone,
    MaskedSSN,
    mask_credit_card,
    mask_email,
    mask_field,
    mask_password,
    mask_phone,
    mask_ssn,
)
from ..models.pagination import PaginatedResponse
from ..models.serialization import to_dict, to_json, to_json_custom


def test_base_entity():
    entity = BaseEntity()
    assert entity.id is not None
    assert entity.created_at is not None
    assert entity.updated_at is not None


def test_base_entity_serialization():
    """Test BaseEntity JSON serialization"""
    entity = BaseEntity()

    # JSON serialization
    json_data = entity.model_dump(mode="json")

    # Check serialized types
    assert isinstance(json_data["id"], str)
    assert isinstance(json_data["created_at"], str)
    assert isinstance(json_data["updated_at"], str)

    # Verify UUID serialization
    assert len(json_data["id"]) == 36  # UUID string format

    # Verify datetime serialization (ISO format)
    assert "T" in json_data["created_at"]
    assert "T" in json_data["updated_at"]


def test_base_entity_datetime_serialization_with_none():
    """Test datetime serialization with None value"""
    entity = BaseEntity()

    json_data = entity.model_dump(mode="json")

    # deleted_at should be None
    assert json_data.get("deleted_at") is None


def test_user_profile():
    profile = UserProfile(
        user_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        username="test",
        email="test@test.com",
    )
    assert profile.username == "test"


def test_user_role():
    assert UserRole.ADMIN == "admin"


def test_paginated_response():
    response = PaginatedResponse.create(items=[1, 2, 3], total=3, page=1, page_size=10)
    assert response.total_pages == 1


def test_to_dict():
    """Test to_dict serialization function"""
    profile = UserProfile(
        user_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        username="test_user",
        email="test@example.com",
    )

    data = to_dict(profile)
    assert isinstance(data, dict)
    assert data["username"] == "test_user"
    assert data["email"] == "test@example.com"


def test_to_dict_exclude_none():
    """Test to_dict with exclude_none option"""
    entity = BaseEntity()
    entity.deleted_at = None

    # Without exclude_none
    data_with_none = to_dict(entity, exclude_none=False)
    assert "deleted_at" in data_with_none

    # With exclude_none
    data_without_none = to_dict(entity, exclude_none=True)
    assert "deleted_at" not in data_without_none


def test_to_json():
    """Test to_json serialization function"""
    profile = UserProfile(
        user_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        username="test_user",
        email="test@example.com",
    )

    json_str = to_json(profile)
    assert isinstance(json_str, str)

    # Parse and verify
    parsed = json.loads(json_str)
    assert parsed["username"] == "test_user"
    assert parsed["email"] == "test@example.com"


def test_to_json_exclude_none():
    """Test to_json with exclude_none option"""
    entity = BaseEntity()
    entity.deleted_at = None

    # Without exclude_none
    json_with_none = to_json(entity, exclude_none=False)
    parsed_with = json.loads(json_with_none)
    assert "deleted_at" in parsed_with

    # With exclude_none
    json_without_none = to_json(entity, exclude_none=True)
    parsed_without = json.loads(json_without_none)
    assert "deleted_at" not in parsed_without


def test_to_json_custom():
    """Test custom JSON serialization with datetime handling"""
    entity = BaseEntity()

    json_str = to_json_custom(entity)
    assert isinstance(json_str, str)

    # Parse and verify datetime serialization
    parsed = json.loads(json_str)
    assert "created_at" in parsed
    assert "T" in str(parsed["created_at"])  # ISO format


# ===== Masking Tests =====


def test_mask_email():
    """Test email masking function"""
    assert mask_email("test@example.com") == "te**@example.com"
    assert mask_email("a@example.com") == "a**@example.com"
    assert mask_email("ab@example.com") == "a**@example.com"  # len <= 2: show 1st char
    assert mask_email("invalid") == "***"
    assert mask_email("") == "***"


def test_mask_phone():
    """Test phone masking function"""
    assert mask_phone("010-1234-5678") == "010-****-5678"
    assert mask_phone("02-1234-5678") == "02-****-5678"
    assert mask_phone("01012345678") == "010-****-5678"
    assert mask_phone("021234567") == "***-****-4567"  # 9 digits: fallback with last 4
    assert mask_phone("") == "***"


def test_mask_password():
    """Test password masking function"""
    assert mask_password("myPassword123") == "********"
    assert mask_password("short") == "********"
    assert mask_password("") == "********"


def test_mask_credit_card():
    """Test credit card masking function"""
    assert mask_credit_card("1234-5678-9012-3456") == "****-****-****-3456"
    assert mask_credit_card("1234567890123456") == "****-****-****-3456"
    assert mask_credit_card("123") == "****-****-****-****"
    assert mask_credit_card("") == "****-****-****-****"


def test_mask_ssn():
    """Test SSN masking function"""
    assert mask_ssn("123456-1234567") == "123456-*******"
    assert mask_ssn("1234561234567") == "123456-*******"
    assert mask_ssn("12345") == "******-*******"
    assert mask_ssn("") == "******-*******"


def test_mask_field():
    """Test generic field masking function"""
    assert mask_field("test@example.com", "email") == "te**@example.com"
    assert mask_field("010-1234-5678", "phone") == "010-****-5678"
    assert mask_field("password123", "password") == "********"
    assert mask_field("1234-5678-9012-3456", "credit_card") == "****-****-****-3456"
    assert mask_field("123456-1234567", "ssn") == "123456-*******"
    assert mask_field("some_value", "unknown") == "so********"  # first 2 chars + 8 stars
    assert mask_field(None, "email") == "***"


def test_masked_email_type():
    """Test MaskedEmail Pydantic type"""

    class UserModel(BaseModel):
        email: MaskedEmail

    user = UserModel(email="test@example.com")

    # Normal access returns original value
    assert user.email == "test@example.com"

    # JSON serialization masks the value
    json_data = user.model_dump(mode="json")
    assert json_data["email"] == "te**@example.com"


def test_masked_phone_type():
    """Test MaskedPhone Pydantic type"""

    class ContactModel(BaseModel):
        phone: MaskedPhone

    contact = ContactModel(phone="010-1234-5678")

    # Normal access returns original value
    assert contact.phone == "010-1234-5678"

    # JSON serialization masks the value
    json_data = contact.model_dump(mode="json")
    assert json_data["phone"] == "010-****-5678"


def test_masked_password_type():
    """Test MaskedPassword Pydantic type"""

    class AuthModel(BaseModel):
        password: MaskedPassword

    auth = AuthModel(password="mySecurePassword123")

    # Normal access returns original value
    assert auth.password == "mySecurePassword123"

    # JSON serialization masks the value
    json_data = auth.model_dump(mode="json")
    assert json_data["password"] == "********"


def test_masked_credit_card_type():
    """Test MaskedCreditCard Pydantic type"""

    class PaymentModel(BaseModel):
        card: MaskedCreditCard

    payment = PaymentModel(card="1234-5678-9012-3456")

    # Normal access returns original value
    assert payment.card == "1234-5678-9012-3456"

    # JSON serialization masks the value
    json_data = payment.model_dump(mode="json")
    assert json_data["card"] == "****-****-****-3456"


def test_masked_ssn_type():
    """Test MaskedSSN Pydantic type"""

    class PersonModel(BaseModel):
        ssn: MaskedSSN

    person = PersonModel(ssn="123456-1234567")

    # Normal access returns original value
    assert person.ssn == "123456-1234567"

    # JSON serialization masks the value
    json_data = person.model_dump(mode="json")
    assert json_data["ssn"] == "123456-*******"
