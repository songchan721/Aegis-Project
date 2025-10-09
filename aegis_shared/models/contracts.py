from uuid import UUID

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: UUID
    username: str
    email: str
