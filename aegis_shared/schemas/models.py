from typing import List

from pydantic import BaseModel


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
    owner: str  # 소유 서비스
    version: str
    description: str
    columns: List[SchemaColumn]
    references: List[SchemaReference] = []
