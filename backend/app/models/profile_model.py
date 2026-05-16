from sqlalchemy import Column, String
from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True)
    display_name = Column(String, nullable=True)
    public_key = Column(String, nullable=True)
    role = Column(String, default="user")