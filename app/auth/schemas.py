from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: str | None = None
    timezone: str = "UTC"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    phone_number: str | None
    email_verified: bool
    phone_verified: bool
    timezone: str
    created_at: datetime
