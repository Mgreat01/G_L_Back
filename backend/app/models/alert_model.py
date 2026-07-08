from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index
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

    encryption_algorithm = Column(
        String,
        nullable=False,
        default="AES-256-GCM"
    )

    encrypted_content_nonce = Column(
        String,
        nullable=True
    )

    encrypted_content_tag = Column(
        String,
        nullable=True
    )

    key_encryption_algorithm = Column(
        String,
        nullable=False,
        default="RSA-OAEP-SHA256"
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
        default="active",
        index=True
    )

    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    address = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    assigned_at = Column(
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

    recipient_keys = relationship(
        "AlertRecipientKey",
        back_populates="alert",
        cascade="all, delete-orphan"
    )

    history = relationship(
        "AlertHistory",
        back_populates="alert",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Index metier pour les listes filtrees puis triees par date.
        Index("ix_alerts_status_created_at", "status", "created_at"),
        Index("ix_alerts_user_id_created_at", "user_id", "created_at"),
        Index("ix_alerts_severity", "severity"),
        # PostGIS utilise un index GiST pour ST_DWithin et les recherches spatiales.
        Index("ix_alerts_location_gist", "location", postgresql_using="gist"),
    )


class AlertRecipientKey(Base):

    __tablename__ = "alert_recipient_keys"

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

    recipient_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    encrypted_key = Column(
        String,
        nullable=False
    )

    key_encryption_algorithm = Column(
        String,
        nullable=False,
        default="RSA-OAEP-SHA256"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    alert = relationship(
        "Alert",
        back_populates="recipient_keys"
    )

    recipient = relationship(
        "User",
        foreign_keys=[recipient_user_id]
    )

    __table_args__ = (
        Index(
            "ux_alert_recipient_keys_alert_recipient",
            "alert_id",
            "recipient_user_id",
            unique=True
        ),
    )


class AlertHistory(Base):

    __tablename__ = "alert_history"

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

    actor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    action = Column(
        String,
        nullable=False,
        index=True
    )

    previous_status = Column(
        String,
        nullable=True
    )

    new_status = Column(
        String,
        nullable=True
    )

    previous_assigned_to = Column(
        UUID(as_uuid=True),
        nullable=True
    )

    new_assigned_to = Column(
        UUID(as_uuid=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    alert = relationship(
        "Alert",
        back_populates="history"
    )

    actor = relationship(
        "User",
        foreign_keys=[actor_user_id]
    )
