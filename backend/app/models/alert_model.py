from sqlalchemy import Column, Integer, String, Boolean
from geoalchemy2 import Geometry

from app.core.database import Base

class Alert(Base):

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)

    encrypted_content = Column(String)

    resolved = Column(Boolean, default=False)

    location = Column(
        Geometry(
            geometry_type='POINT',
            srid=4326
        )
    )