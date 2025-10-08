import yaml
from pathlib import Path
from typing import Dict, List
from .models import SchemaDefinition

class SchemaRegistry:
    def __init__(self, schema_dir: str):
        self.schema_dir = Path(schema_dir)
        self.schemas: Dict[str, SchemaDefinition] = {}
        self.load_schemas()

    def load_schemas(self):
        for file_path in self.schema_dir.glob("*.yaml"):
            with open(file_path, 'r') as f:
                schema_data = yaml.safe_load(f)
                schema = SchemaDefinition(**schema_data)
                self.schemas[schema.name] = schema

    def get_schema(self, name: str) -> SchemaDefinition:
        return self.schemas.get(name)

    def analyze_dependencies(self) -> Dict[str, List[str]]:
        dependency_graph = {name: [ref.schema for ref in schema.references] for name, schema in self.schemas.items()}
        return dependency_graph

    def generate_markdown_docs(self) -> str:
        docs = ""
        for schema in self.get_all_schemas():
            docs += f"# {schema.name} (v{schema.version})\n\n"
            docs += f"{schema.description}\n\n"
            docs += f"## Columns\n\n"
            docs += f"| Name | Type | Description | Required |\n"
            docs += f"|---|---|---|---|\n"

            for col in schema.columns:
                docs += f"| {col.name} | {col.type} | {col.description} | {col.required} |\n"
            docs += "\n"

            if schema.references:
                docs += f"## References\n\n"
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
