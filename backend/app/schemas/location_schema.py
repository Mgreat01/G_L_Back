from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class LocationCreate(BaseModel):
    alert_id: UUID
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None


class LocationResponse(BaseModel):
    id: UUID
    alert_id: UUID
    latitude: float
    longitude: float
    accuracy: Optional[float]

    class Config:
        from_attributes = True