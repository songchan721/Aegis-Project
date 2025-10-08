import pytest
from ..models.base import BaseEntity
from ..models.contracts import UserProfile
from ..models.enums import UserRole
from ..models.pagination import PaginatedResponse

def test_base_entity():
    entity = BaseEntity()
    assert entity.id is not None
    assert entity.created_at is not None
    assert entity.updated_at is not None

def test_user_profile():
    profile = UserProfile(user_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", username="test", email="test@test.com")
    assert profile.username == "test"

def test_user_role():
    assert UserRole.ADMIN == "admin"

def test_paginated_response():
    response = PaginatedResponse.create(items=[1, 2, 3], total=3, page=1, page_size=10)
    assert response.total_pages == 1
