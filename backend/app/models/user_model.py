import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func

from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    username = Column(
        String,
        unique=True,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        default="user",
        index=True
    )

    public_key = Column(
        String,
        nullable=True
    )

    public_key_algorithm = Column(
        String,
        nullable=True
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

    email_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )

    is_rescuer = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
