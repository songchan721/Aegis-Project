from typing import List, Dict
from .models import MigrationStep
from ..schemas.registry import SchemaRegistry

class MigrationCoordinator:
    def __init__(self, schema_registry: SchemaRegistry):
        self.schema_registry = schema_registry
        self.history: List[List[MigrationStep]] = []
        self.schema_registry = schema_registry

    def plan_migration(self, services_to_migrate: List[str]) -> List[MigrationStep]:
        """Create a migration plan based on service dependencies."""
        dependency_graph = self.schema_registry.analyze_dependencies()
        
        # Simple topological sort to determine order
        migration_order = []
        visited = set()

        def visit(service):
            if service not in visited:
                visited.add(service)
                for dependency in dependency_graph.get(service, []):
                    visit(dependency)
                if service in services_to_migrate:
                    migration_order.append(service)

        for service in services_to_migrate:
            visit(service)

        return [MigrationStep(service=s, version="latest", description=f"Migrate {s}") for s in migration_order]

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
                # In a real implementation, you would trigger the rollback for the service.
                step.status = "rolled_back"
                print(f"Rollback for {step.service} completed.")
