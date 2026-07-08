from pydantic import BaseModel, Field
from typing import Optional, Any, Literal
from uuid import UUID
from datetime import datetime


AlertStatus = Literal[
    "active",
    "acknowledged",
    "assigned",
    "resolved",
    "cancelled"
]

AlertSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical"
]


class AlertRecipientKeyCreate(BaseModel):

    recipient_user_id: UUID

    encrypted_key: str = Field(min_length=16, max_length=20000)

    key_encryption_algorithm: Literal[
        "RSA-OAEP-SHA256",
        "ECDH-ES+A256KW"
    ] = "RSA-OAEP-SHA256"


class AlertRecipientKeyResponse(BaseModel):

    recipient_user_id: UUID

    encrypted_key: str

    key_encryption_algorithm: str

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertCreate(BaseModel):

    encrypted_content: str = Field(min_length=16, max_length=500000)

    encrypted_key: str = Field(min_length=16, max_length=20000)

    encryption_algorithm: Literal[
        "AES-256-GCM"
    ] = "AES-256-GCM"

    encrypted_content_nonce: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=256
    )

    encrypted_content_tag: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=256
    )

    key_encryption_algorithm: Literal[
        "RSA-OAEP-SHA256",
        "ECDH-ES+A256KW"
    ] = "RSA-OAEP-SHA256"

    recipient_keys: list[AlertRecipientKeyCreate] = Field(default_factory=list)

    latitude: float = Field(
        ...,
        ge=-90,
        le=90
    )

    longitude: float = Field(
        ...,
        ge=-180,
        le=180
    )

    severity: AlertSeverity = "high"


class AlertUpdate(BaseModel):

    status: Optional[AlertStatus] = None

    assigned_to: Optional[UUID] = None

    severity: Optional[AlertSeverity] = None


class AlertResponse(BaseModel):

    id: UUID

    user_id: UUID

    encrypted_content: str

    encrypted_key: str

    encryption_algorithm: Optional[str] = None

    encrypted_content_nonce: Optional[str] = None

    encrypted_content_tag: Optional[str] = None

    key_encryption_algorithm: Optional[str] = None

    recipient_keys: list[AlertRecipientKeyResponse] = Field(default_factory=list)

    latitude: float

    longitude: float

    location: Any

    severity: str

    status: str

    assigned_to: Optional[UUID] = None

    created_at: Optional[datetime] = None

    acknowledged_at: Optional[datetime] = None

    assigned_at: Optional[datetime] = None

    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):

    id: UUID

    alert_id: UUID

    actor_user_id: Optional[UUID] = None

    action: str

    previous_status: Optional[str] = None

    new_status: Optional[str] = None

    previous_assigned_to: Optional[UUID] = None

    new_assigned_to: Optional[UUID] = None

    created_at: datetime

    class Config:
        from_attributes = True
