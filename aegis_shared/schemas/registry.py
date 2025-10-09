from pathlib import Path
from typing import Dict, List, Set

import yaml

from .models import SchemaDefinition


class SchemaRegistry:
    def __init__(self, schema_dir: str):
        self.schema_dir = Path(schema_dir)
        self.schemas: Dict[str, SchemaDefinition] = {}
        self.load_schemas()

    def load_schemas(self):
        for file_path in self.schema_dir.glob("*.yaml"):
            with open(file_path, "r") as f:
                schema_data = yaml.safe_load(f)
                schema = SchemaDefinition(**schema_data)
                self.schemas[schema.name] = schema

    def get_schema(self, name: str) -> SchemaDefinition:
        return self.schemas.get(name)

    def get_all_schemas(self) -> List[SchemaDefinition]:
        """모든 스키마 반환"""
        return list(self.schemas.values())

    def analyze_dependencies(self) -> Dict[str, List[str]]:
        dependency_graph = {
            name: [ref.schema for ref in schema.references]
            for name, schema in self.schemas.items()
        }
        return dependency_graph

    def generate_markdown_docs(self) -> str:
        docs = ""
        for schema in self.get_all_schemas():
            docs += f"# {schema.name} (v{schema.version})\n\n"
            docs += f"{schema.description}\n\n"
            docs += "## Columns\n\n"
            docs += "| Name | Type | Description | Required |\n"
            docs += "|---|---|---|---|\n"

            for col in schema.columns:
                docs += (
                    f"| {col.name} | {col.type} | "
                    f"{col.description} | {col.required} |\n"
                )
            docs += "\n"

            if schema.references:
                docs += "## References\n\n"
                for ref in schema.references:
                    docs += f"- {ref.service}/{ref.schema}\n"
                docs += "\n"
        return docs

    def generate_mermaid_graph(self) -> str:
        graph = self.analyze_dependencies()
        mermaid = "graph TD;\n"
        for node, deps in graph.items():
            for dep in deps:
                mermaid += f"    {node} --> {dep};\n"
        return mermaid

    def get_dependent_services(self, schema_name: str) -> Set[str]:
        """특정 스키마에 의존하는 서비스 목록"""
        dependent_services = set()

        for schema in self.schemas.values():
            for ref in schema.references:
                if ref.schema == schema_name:
                    dependent_services.add(schema.owner)

        return dependent_services

    def validate_references(self) -> List[str]:
        """참조 무결성 검증"""
        errors = []

        for schema_name, schema in self.schemas.items():
            for ref in schema.references:
                if ref.schema not in self.schemas:
                    errors.append(
                        f"Schema '{schema_name}' references "
                        f"non-existent schema '{ref.schema}'"
                    )

        return errors

    def generate_migration_order(self) -> List[str]:
        """마이그레이션 실행 순서 생성 (위상 정렬)"""
        graph = self.analyze_dependencies()

        # 각 스키마의 남은 의존성 개수 추적
        remaining_deps = {schema: len(deps) for schema, deps in graph.items()}

        # 의존성이 없는 스키마부터 시작
        queue = [schema for schema, deps in graph.items() if len(deps) == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # node에 의존하는 스키마들을 찾아 의존성 감소
            for schema, dependencies in graph.items():
                if node in dependencies:
                    remaining_deps[schema] -= 1
                    if remaining_deps[schema] == 0:
                        queue.append(schema)

        return result
