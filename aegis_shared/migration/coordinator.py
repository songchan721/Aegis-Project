from typing import Dict, List

from ..schemas.registry import SchemaRegistry
from .models import MigrationStep


class MigrationCoordinator:
    def __init__(self, schema_registry: SchemaRegistry):
        self.schema_registry = schema_registry
        self.history: List[List[MigrationStep]] = []
        self.schema_registry = schema_registry

    def plan_migration(self, schema_changes: Dict[str, str]) -> List[MigrationStep]:
        """Create a migration plan based on schema dependencies."""
        # Get migration order from schema registry
        migration_order = self.schema_registry.generate_migration_order()

        # Create migration steps only for schemas in schema_changes
        steps = []
        for schema_name in migration_order:
            if schema_name in schema_changes:
                # Get schema definition
                schema_def = self.schema_registry.get_schema(schema_name)
                if schema_def:
                    step = MigrationStep(
                        service=schema_def.owner,
                        schema=schema_name,
                        version=schema_def.version,
                        description=f"Migrate {schema_name}",
                        sql=schema_changes[schema_name],
                    )
                    steps.append(step)

        return steps

    def validate_migration(self, plan: List[MigrationStep]) -> bool:
        """Validate the migration plan for potential issues."""
        # In a real implementation, you would check for breaking changes,
        # data loss, etc.
        print("Validating migration plan...")

    def rollback(self, plan: List[MigrationStep]):
        """Roll back a migration plan."""
        for step in reversed(plan):
            if step.status == "completed":
                print(f"Rolling back migration for {step.service}...")
                # In a real implementation, you would trigger the rollback
                # for the service.
                step.status = "rolled_back"
                print(f"Rollback for {step.service} completed.")
