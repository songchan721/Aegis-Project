from ..models.base import BaseEntity
from ..models.contracts import UserProfile
from ..models.enums import UserRole
from ..models.pagination import PaginatedResponse


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
