from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from app.models.location_model import LocationUpdate
from app.models.alert_model import Alert

from app.schemas.location_schema import LocationCreate


class LocationService:

    @staticmethod
    def create_location(
        db: Session,
        location: LocationCreate
    ):

        alert = db.query(Alert).filter(
            Alert.id == location.alert_id
        ).first()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Vérifie si l'alerte est active
        if alert.status not in ["active", "acknowledged"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update location for resolved/cancelled alert"
            )

        try:

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

        except SQLAlchemyError as e:

            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

    @staticmethod
    def get_locations(
        db: Session,
        alert_id: str
    ):

        # Vérifie si l'alerte existe
        alert = db.query(Alert).filter(
            Alert.id == alert_id
        ).first()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        locations = db.query(LocationUpdate)\
            .filter(LocationUpdate.alert_id == alert_id)\
            .order_by(LocationUpdate.created_at.desc())\
            .all()

        return locations