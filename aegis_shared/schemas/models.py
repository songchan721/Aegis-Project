from pydantic import BaseModel, Field
from typing import List, Dict, Any

class SchemaColumn(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True

class SchemaReference(BaseModel):
    service: str
    schema: str

class SchemaDefinition(BaseModel):
    name: str
    version: str
    description: str
    columns: List[SchemaColumn]
    references: List[SchemaReference] = []
