import tempfile
from pathlib import Path

import pytest
import yaml

from ..schemas.registry import SchemaRegistry


@pytest.fixture
def temp_schema_dir():
    """임시 스키마 디렉토리 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_schemas(temp_schema_dir):
    """샘플 스키마 파일 생성"""
    # users 스키마 (의존성 없음)
    users_schema = {
        "name": "users",
        "version": "1.0.0",
        "owner": "user-service",
        "description": "User accounts",
        "columns": [
            {"name": "id", "type": "UUID", "required": True, "description": "User ID"},
            {
                "name": "email",
                "type": "VARCHAR(255)",
                "required": True,
                "description": "Email",
            },
            {
                "name": "name",
                "type": "VARCHAR(100)",
                "required": True,
                "description": "Name",
            },
        ],
        "references": [],
    }

    # policies 스키마 (users에 의존)
    policies_schema = {
        "name": "policies",
        "version": "1.0.0",
        "owner": "policy-service",
        "description": "Policy data",
        "columns": [
            {
                "name": "id",
                "type": "UUID",
                "required": True,
                "description": "Policy ID",
            },
            {
                "name": "user_id",
                "type": "UUID",
                "required": True,
                "description": "User ID",
            },
            {
                "name": "title",
                "type": "VARCHAR(200)",
                "required": True,
                "description": "Title",
            },
        ],
        "references": [{"service": "user-service", "schema": "users"}],
    }

    # applications 스키마 (users와 policies에 의존)
    applications_schema = {
        "name": "applications",
        "version": "1.0.0",
        "owner": "application-service",
        "description": "Policy applications",
        "columns": [
            {
                "name": "id",
                "type": "UUID",
                "required": True,
                "description": "Application ID",
            },
            {
                "name": "user_id",
                "type": "UUID",
                "required": True,
                "description": "User ID",
            },
            {
                "name": "policy_id",
                "type": "UUID",
                "required": True,
                "description": "Policy ID",
            },
        ],
        "references": [
            {"service": "user-service", "schema": "users"},
            {"service": "policy-service", "schema": "policies"},
        ],
    }

    # 파일 저장
    with open(temp_schema_dir / "users.yaml", "w") as f:
        yaml.dump(users_schema, f)

    with open(temp_schema_dir / "policies.yaml", "w") as f:
        yaml.dump(policies_schema, f)

    with open(temp_schema_dir / "applications.yaml", "w") as f:
        yaml.dump(applications_schema, f)

    return temp_schema_dir


class TestSchemaRegistry:
    """SchemaRegistry 테스트"""

    def test_load_schemas(self, sample_schemas):
        """스키마 로드 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        assert len(registry.schemas) == 3
        assert "users" in registry.schemas
        assert "policies" in registry.schemas
        assert "applications" in registry.schemas

    def test_get_schema(self, sample_schemas):
        """개별 스키마 조회 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        users_schema = registry.get_schema("users")
        assert users_schema is not None
        assert users_schema.name == "users"
        assert users_schema.version == "1.0.0"
        assert users_schema.owner == "user-service"

        # 존재하지 않는 스키마
        assert registry.get_schema("nonexistent") is None

    def test_get_all_schemas(self, sample_schemas):
        """모든 스키마 조회 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        all_schemas = registry.get_all_schemas()
        assert len(all_schemas) == 3

        schema_names = {s.name for s in all_schemas}
        assert schema_names == {"users", "policies", "applications"}

    def test_analyze_dependencies(self, sample_schemas):
        """의존성 분석 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        deps = registry.analyze_dependencies()

        # users는 의존성 없음
        assert deps["users"] == []

        # policies는 users에 의존
        assert deps["policies"] == ["users"]

        # applications는 users와 policies에 의존
        assert set(deps["applications"]) == {"users", "policies"}

    def test_generate_migration_order(self, sample_schemas):
        """마이그레이션 순서 생성 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        order = registry.generate_migration_order()

        # users가 가장 먼저 와야 함
        assert order[0] == "users"

        # policies는 users 다음에 와야 함
        users_idx = order.index("users")
        policies_idx = order.index("policies")
        assert policies_idx > users_idx

        # applications는 users와 policies 다음에 와야 함
        applications_idx = order.index("applications")
        assert applications_idx > users_idx
        assert applications_idx > policies_idx

    def test_get_dependent_services(self, sample_schemas):
        """의존 서비스 조회 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        # users에 의존하는 서비스
        users_dependents = registry.get_dependent_services("users")
        assert users_dependents == {"policy-service", "application-service"}

        # policies에 의존하는 서비스
        policies_dependents = registry.get_dependent_services("policies")
        assert policies_dependents == {"application-service"}

        # applications에 의존하는 서비스는 없음
        applications_dependents = registry.get_dependent_services("applications")
        assert applications_dependents == set()

    def test_validate_references_valid(self, sample_schemas):
        """참조 무결성 검증 - 성공 케이스"""
        registry = SchemaRegistry(str(sample_schemas))

        errors = registry.validate_references()
        assert errors == []

    def test_validate_references_invalid(self, temp_schema_dir):
        """참조 무결성 검증 - 실패 케이스"""
        # 존재하지 않는 스키마를 참조하는 스키마 생성
        invalid_schema = {
            "name": "invalid",
            "version": "1.0.0",
            "owner": "test-service",
            "description": "Invalid schema",
            "columns": [
                {"name": "id", "type": "UUID", "required": True, "description": "ID"}
            ],
            "references": [{"service": "nonexistent-service", "schema": "nonexistent"}],
        }

        with open(temp_schema_dir / "invalid.yaml", "w") as f:
            yaml.dump(invalid_schema, f)

        registry = SchemaRegistry(str(temp_schema_dir))

        errors = registry.validate_references()
        assert len(errors) == 1
        assert "invalid" in errors[0]
        assert "nonexistent" in errors[0]

    def test_generate_markdown_docs(self, sample_schemas):
        """Markdown 문서 생성 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        docs = registry.generate_markdown_docs()

        # 모든 스키마가 문서에 포함되어야 함
        assert "users" in docs
        assert "policies" in docs
        assert "applications" in docs

        # 버전 정보 포함
        assert "v1.0.0" in docs

        # 컬럼 정보 포함
        assert "id" in docs
        assert "email" in docs
        assert "UUID" in docs

        # 참조 정보 포함
        assert "References" in docs
        assert "user-service/users" in docs

    def test_generate_mermaid_graph(self, sample_schemas):
        """Mermaid 그래프 생성 테스트"""
        registry = SchemaRegistry(str(sample_schemas))

        mermaid = registry.generate_mermaid_graph()

        # Mermaid 형식 확인
        assert mermaid.startswith("graph TD;")

        # 의존성 화살표 확인
        assert "policies --> users" in mermaid
        assert "applications --> users" in mermaid
        assert "applications --> policies" in mermaid

    def test_empty_schema_dir(self, temp_schema_dir):
        """빈 디렉토리 테스트"""
        registry = SchemaRegistry(str(temp_schema_dir))

        assert len(registry.schemas) == 0
        assert registry.get_all_schemas() == []
        assert registry.analyze_dependencies() == {}
        assert registry.generate_migration_order() == []
