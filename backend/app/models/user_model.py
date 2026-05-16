from sqlalchemy import Column, Integer, String
from backend.app.core.database import Base

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    username = Column(String, unique=True)

    email = Column(String, unique=True)

    hashed_password = Column(String)

    role = Column(String)

    public_key = Column(String)