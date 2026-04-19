from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid

from app.core.database import Base

class LocationUpdate(Base):
    __tablename__ = "location_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"))

    user_id = Column(UUID(as_uuid=True))

    latitude = Column(Float)
    longitude = Column(Float)

    location = Column(
        Geometry(geometry_type='POINT', srid=4326)
    )

    accuracy = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())