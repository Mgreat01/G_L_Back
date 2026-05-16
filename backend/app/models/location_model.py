from sqlalchemy import Column, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

import uuid

from app.core.database import Base


class LocationUpdate(Base):

    __tablename__ = "location_updates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    alert_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id")
    )

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    accuracy = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )