from sqlalchemy import select
from sqlalchemy.orm import Session, load_only
from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException, status

from app.models.location_model import LocationUpdate
from app.models.alert_model import Alert

from app.schemas.location_schema import LocationCreate

from app.utils.gps import create_point


class LocationService:

    @staticmethod
    def create_location(
        db: Session,
        location: LocationCreate,
        current_user
    ):

        alert = db.query(Alert) \
            .options(
                load_only(
                    Alert.id,
                    Alert.user_id,
                    Alert.status
                )
            ) \
            .filter(Alert.id == location.alert_id) \
            .first()

        if not alert:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        is_owner = (
            str(alert.user_id)
            == current_user["id"]
        )

        is_rescuer = current_user["role"] in [
            "rescuer",
            "admin",
            "operator"
        ]

        if not is_owner and not is_rescuer:

            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        if alert.status not in [
            "active",
            "acknowledged"
        ]:

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

            alert.latitude = location.latitude

            alert.longitude = location.longitude

            alert.location = create_point(
                location.longitude,
                location.latitude
            )
            # Les coordonnees ont change : l'adresse stockee ne doit pas rester stale.
            alert.address = None

            db.commit()

            db.refresh(db_location)

            return {
                "message": "Location updated successfully",
                "location": {
                    "id": str(db_location.id),
                    "alert_id": str(db_location.alert_id),
                    "latitude": db_location.latitude,
                    "longitude": db_location.longitude,
                    "accuracy": db_location.accuracy,
                    "created_at": db_location.created_at
                }
            }

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

        alert_exists = db.execute(
            select(Alert.id).where(Alert.id == alert_id)
        ).first()

        if not alert_exists:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        locations = db.query(LocationUpdate)\
            .options(
                load_only(
                    LocationUpdate.id,
                    LocationUpdate.alert_id,
                    LocationUpdate.latitude,
                    LocationUpdate.longitude,
                    LocationUpdate.accuracy,
                    LocationUpdate.created_at
                )
            )\
            .filter(
                LocationUpdate.alert_id == alert_id
            )\
            .order_by(
                LocationUpdate.created_at.desc()
            )\
            .all()

        return locations
