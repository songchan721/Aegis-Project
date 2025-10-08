from pydantic import BaseModel
from uuid import UUID

class UserProfile(BaseModel):
    user_id: UUID
    username: str
    email: str
