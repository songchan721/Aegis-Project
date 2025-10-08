from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict

class MigrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class MigrationStep(BaseModel):
    service: str
    version: str
    description: str
    status: MigrationStatus = MigrationStatus.PENDING
    dependencies: List[str] = []
