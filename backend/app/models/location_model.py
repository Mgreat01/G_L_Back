from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index
)

from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

from sqlalchemy.types import DateTime

from geoalchemy2 import Geometry

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
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    accuracy = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    alert = relationship(
        "Alert",
        back_populates="locations"
    )

    __table_args__ = (
        Index("ix_location_updates_alert_id_created_at", "alert_id", "created_at"),
    )


class RescueTeamLocation(Base):

    __tablename__ = "rescue_team_locations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    accuracy = Column(Float)

    location = Column(
        Geometry(
            geometry_type="POINT",
            srid=4326
        )
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    user = relationship("User")

    __table_args__ = (
        Index("ix_rescue_team_locations_user_created_at", "user_id", "created_at"),
        Index("ix_rescue_team_locations_location_gist", "location", postgresql_using="gist"),
    )
