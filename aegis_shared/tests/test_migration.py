import tempfile
from pathlib import Path

import pytest
import yaml

from ..migration.coordinator import MigrationCoordinator
from ..migration.models import MigrationStatus, MigrationStep
from ..schemas.registry import SchemaRegistry


@pytest.fixture
def temp_schema_dir():
    """임시 스키마 디렉토리 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_schemas(temp_schema_dir):
    """샘플 스키마 파일 생성"""
    # users 스키마
    users_schema = {
        "name": "users",
        "version": "1.0.0",
        "owner": "user-service",
        "description": "User accounts",
        "columns": [
            {"name": "id", "type": "UUID", "required": True, "description": "User ID"}
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
            {"name": "id", "type": "UUID", "required": True, "description": "Policy ID"}
        ],
        "references": [{"service": "user-service", "schema": "users"}],
    }

    with open(temp_schema_dir / "users.yaml", "w") as f:
        yaml.dump(users_schema, f)

    with open(temp_schema_dir / "policies.yaml", "w") as f:
        yaml.dump(policies_schema, f)

    return temp_schema_dir


@pytest.fixture
def schema_registry(sample_schemas):
    """SchemaRegistry fixture"""
    return SchemaRegistry(str(sample_schemas))


@pytest.fixture
def coordinator(schema_registry):
    """MigrationCoordinator fixture"""
    return MigrationCoordinator(schema_registry)


class TestMigrationCoordinator:
    """MigrationCoordinator 테스트"""

    def test_init(self, schema_registry):
        """초기화 테스트"""
        coordinator = MigrationCoordinator(schema_registry)

        assert coordinator.schema_registry is schema_registry
        assert coordinator.history == []

    def test_plan_migration_empty(self, coordinator):
        """빈 변경사항으로 마이그레이션 계획 테스트"""
        plan = coordinator.plan_migration({})

        assert plan == []

    def test_plan_migration_single_schema(self, coordinator):
        """단일 스키마 마이그레이션 계획 테스트"""
        schema_changes = {"users": "ALTER TABLE users ADD COLUMN age INT;"}

        plan = coordinator.plan_migration(schema_changes)

        assert len(plan) == 1
        assert plan[0].service == "user-service"
        assert plan[0].schema == "users"
        assert plan[0].version == "1.0.0"
        assert plan[0].description == "Migrate users"
        assert plan[0].sql == "ALTER TABLE users ADD COLUMN age INT;"
        assert plan[0].status == MigrationStatus.PENDING

    def test_plan_migration_multiple_schemas(self, coordinator):
        """여러 스키마 마이그레이션 계획 테스트"""
        schema_changes = {
            "users": "ALTER TABLE users ADD COLUMN age INT;",
            "policies": "ALTER TABLE policies ADD COLUMN status VARCHAR(50);",
        }

        plan = coordinator.plan_migration(schema_changes)

        assert len(plan) == 2

        # users가 먼저 와야 함 (policies가 users에 의존)
        assert plan[0].schema == "users"
        assert plan[1].schema == "policies"

        # 각 step 검증
        assert plan[0].service == "user-service"
        assert plan[0].sql == "ALTER TABLE users ADD COLUMN age INT;"

        assert plan[1].service == "policy-service"
        assert plan[1].sql == "ALTER TABLE policies ADD COLUMN status VARCHAR(50);"

    def test_plan_migration_dependency_order(self, coordinator):
        """의존성 순서 유지 테스트"""
        # policies만 변경 (users는 변경 없음)
        schema_changes = {"policies": "ALTER TABLE policies ADD COLUMN active BOOLEAN;"}

        plan = coordinator.plan_migration(schema_changes)

        # policies만 계획에 포함되어야 함
        assert len(plan) == 1
        assert plan[0].schema == "policies"

    def test_plan_migration_nonexistent_schema(self, coordinator):
        """존재하지 않는 스키마에 대한 변경사항 테스트"""
        schema_changes = {"nonexistent": "CREATE TABLE nonexistent (id UUID);"}

        plan = coordinator.plan_migration(schema_changes)

        # 존재하지 않는 스키마는 무시됨
        assert plan == []

    def test_validate_migration(self, coordinator, capsys):
        """마이그레이션 검증 테스트"""
        plan = [
            MigrationStep(
                service="user-service",
                schema="users",
                version="1.0.0",
                description="Test migration",
                sql="ALTER TABLE users ADD COLUMN test INT;",
            )
        ]

        result = coordinator.validate_migration(plan)

        # validate_migration은 print만 하고 None 반환
        captured = capsys.readouterr()
        assert "Validating migration plan" in captured.out
        assert result is None

    def test_rollback_empty_plan(self, coordinator, capsys):
        """빈 계획에 대한 롤백 테스트"""
        coordinator.rollback([])

        # 아무 것도 출력되지 않아야 함
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_rollback_completed_migrations(self, coordinator, capsys):
        """완료된 마이그레이션 롤백 테스트"""
        plan = [
            MigrationStep(
                service="user-service",
                schema="users",
                version="1.0.0",
                description="Test migration 1",
                sql="ALTER TABLE users ADD COLUMN test1 INT;",
                status=MigrationStatus.COMPLETED,
            ),
            MigrationStep(
                service="policy-service",
                schema="policies",
                version="1.0.0",
                description="Test migration 2",
                sql="ALTER TABLE policies ADD COLUMN test2 INT;",
                status=MigrationStatus.COMPLETED,
            ),
        ]

        coordinator.rollback(plan)

        # 역순으로 롤백되어야 함
        captured = capsys.readouterr()
        output = captured.out

        assert "Rolling back migration for policy-service" in output
        assert "Rolling back migration for user-service" in output
        assert "Rollback for policy-service completed" in output
        assert "Rollback for user-service completed" in output

        # 상태가 rolled_back로 변경되어야 함
        assert plan[0].status == "rolled_back"
        assert plan[1].status == "rolled_back"

    def test_rollback_pending_migrations(self, coordinator, capsys):
        """대기 중인 마이그레이션 롤백 테스트 (롤백 안 됨)"""
        plan = [
            MigrationStep(
                service="user-service",
                schema="users",
                version="1.0.0",
                description="Test migration",
                sql="ALTER TABLE users ADD COLUMN test INT;",
                status=MigrationStatus.PENDING,
            )
        ]

        coordinator.rollback(plan)

        # pending 상태는 롤백하지 않음
        captured = capsys.readouterr()
        assert "Rolling back migration" not in captured.out

        # 상태가 변경되지 않아야 함
        assert plan[0].status == MigrationStatus.PENDING

    def test_rollback_mixed_status(self, coordinator, capsys):
        """혼합 상태 마이그레이션 롤백 테스트"""
        plan = [
            MigrationStep(
                service="user-service",
                schema="users",
                version="1.0.0",
                description="Test migration 1",
                sql="ALTER TABLE users ADD COLUMN test1 INT;",
                status=MigrationStatus.PENDING,
            ),
            MigrationStep(
                service="policy-service",
                schema="policies",
                version="1.0.0",
                description="Test migration 2",
                sql="ALTER TABLE policies ADD COLUMN test2 INT;",
                status=MigrationStatus.COMPLETED,
            ),
        ]

        coordinator.rollback(plan)

        # completed만 롤백되어야 함
        captured = capsys.readouterr()
        output = captured.out

        assert "Rolling back migration for policy-service" in output
        assert "Rolling back migration for user-service" not in output

        # completed만 상태 변경
        assert plan[0].status == MigrationStatus.PENDING
        assert plan[1].status == "rolled_back"
