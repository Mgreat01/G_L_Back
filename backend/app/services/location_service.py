from sqlalchemy.orm import Session

from app.models.location_model import LocationUpdate
from app.schemas.location_schema import LocationCreate


class LocationService:

    @staticmethod
    def create_location(db: Session, location: LocationCreate):

        db_location = LocationUpdate(
            alert_id=location.alert_id,
            latitude=location.latitude,
            longitude=location.longitude,
            accuracy=location.accuracy
        )

        db.add(db_location)

        db.commit()

        db.refresh(db_location)

        return db_location

    @staticmethod
    def get_locations(db: Session, alert_id: str):

        return db.query(LocationUpdate)\
            .filter(LocationUpdate.alert_id == alert_id)\
            .all()