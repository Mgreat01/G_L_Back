import uuid

from sqlalchemy import Column, Integer, String
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class User(Base):

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    username = Column(String, unique=True)

    email = Column(String, unique=True)

    hashed_password = Column(String)

    role = Column(String)

    public_key = Column(String)