"""
메인 애플리케이션 테스트
"""

import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """헬스 체크 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "sample-service"}

def test_metrics_endpoint(client: TestClient):
    """메트릭 엔드포인트 테스트"""
    response = client.get("/metrics")
    assert response.status_code == 200

def test_login_success(client: TestClient):
    """로그인 성공 테스트"""
    response = client.post("/auth/login", params={
        "email": "admin@example.com",
        "password": "password"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure(client: TestClient):
    """로그인 실패 테스트"""
    response = client.post("/auth/login", params={
        "email": "wrong@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_user(client: TestClient, auth_headers: dict, sample_user_data: dict):
    """사용자 생성 테스트"""
    response = client.post(
        "/users/",
        json=sample_user_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["name"] == sample_user_data["name"]
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: TestClient, auth_headers: dict, sample_user_data: dict):
    """중복 이메일로 사용자 생성 테스트"""
    # 첫 번째 사용자 생성
    client.post("/users/", json=sample_user_data, headers=auth_headers)
    
    # 같은 이메일로 두 번째 사용자 생성 시도
    response = client.post("/users/", json=sample_user_data, headers=auth_headers)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_list_users(client: TestClient, auth_headers: dict):
    """사용자 목록 조회 테스트"""
    response = client.get("/users/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

@pytest.mark.asyncio
async def test_get_user(client: TestClient, auth_headers: dict, sample_user_data: dict):
    """사용자 조회 테스트"""
    # 사용자 생성
    create_response = client.post("/users/", json=sample_user_data, headers=auth_headers)
    user_id = create_response.json()["id"]
    
    # 사용자 조회
    response = client.get(f"/users/{user_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == sample_user_data["email"]

@pytest.mark.asyncio
async def test_get_user_not_found(client: TestClient, auth_headers: dict):
    """존재하지 않는 사용자 조회 테스트"""
    response = client.get("/users/non-existent-id", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_user(client: TestClient, auth_headers: dict, sample_user_data: dict):
    """사용자 업데이트 테스트"""
    # 사용자 생성
    create_response = client.post("/users/", json=sample_user_data, headers=auth_headers)
    user_id = create_response.json()["id"]
    
    # 사용자 업데이트
    update_data = {"name": "Updated Name"}
    response = client.put(f"/users/{user_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"

@pytest.mark.asyncio
async def test_delete_user(client: TestClient, auth_headers: dict, sample_user_data: dict):
    """사용자 삭제 테스트"""
    # 사용자 생성
    create_response = client.post("/users/", json=sample_user_data, headers=auth_headers)
    user_id = create_response.json()["id"]
    
    # 사용자 삭제
    response = client.delete(f"/users/{user_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"

@pytest.mark.asyncio
async def test_get_user_analytics(client: TestClient, auth_headers: dict, sample_user_data: dict):
    """사용자 분석 데이터 조회 테스트"""
    # 사용자 생성
    create_response = client.post("/users/", json=sample_user_data, headers=auth_headers)
    user_id = create_response.json()["id"]
    
    # 분석 데이터 조회
    response = client.get(f"/users/{user_id}/analytics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert "login_count" in data
    assert "activity_score" in data

def test_unauthorized_access(client: TestClient):
    """인증 없이 접근 테스트"""
    response = client.get("/users/")
    assert response.status_code == 401