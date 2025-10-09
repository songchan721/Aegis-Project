from enum import Enum
from typing import List

from pydantic import BaseModel


class MigrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationStep(BaseModel):
    service: str
    schema: str
    version: str
    description: str
    sql: str = ""
    status: MigrationStatus = MigrationStatus.PENDING
    dependencies: List[str] = []
