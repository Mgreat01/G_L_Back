from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

from geoalchemy2 import Geometry

import uuid

from app.core.database import Base


class Alert(Base):

    __tablename__ = "alerts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    encrypted_content = Column(
        String,
        nullable=False
    )

    encrypted_key = Column(
        String,
        nullable=False
    )

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    location = Column(
        Geometry(
            geometry_type="POINT",
            srid=4326
        )
    )

    severity = Column(
        String,
        default="high"
    )

    status = Column(
        String,
        default="active"
    )

    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    creator = relationship(
        "User",
        foreign_keys=[user_id]
    )

    assigned_rescuer = relationship(
        "User",
        foreign_keys=[assigned_to]
    )

    locations = relationship(
        "LocationUpdate",
        back_populates="alert",
        cascade="all, delete"
    )