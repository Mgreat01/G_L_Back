from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class AlertCreate(BaseModel):
    encrypted_content: str
    encrypted_key: str

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    severity: str


class AlertUpdate(BaseModel):
    status: str
    assigned_to: Optional[UUID] = None


class AlertResponse(BaseModel):
    id: UUID
    user_id: UUID

    encrypted_content: str
    encrypted_key: str

    latitude: float
    longitude: float

    severity: str
    status: str

    class Config:
        from_attributes = True