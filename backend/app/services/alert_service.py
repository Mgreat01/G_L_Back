from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.models.alert_model import Alert
from app.schemas.alert_schema import AlertCreate, AlertUpdate
from app.utils.gps import create_point

class AlertService:

    @staticmethod
    def create_alert(db: Session, payload: AlertCreate, user_id):

        alert = Alert(
            user_id=user_id,

            encrypted_content=payload.encrypted_content,
            encrypted_key=payload.encrypted_key,

            latitude=payload.latitude,
            longitude=payload.longitude,

            location=create_point(
                payload.longitude,
                payload.latitude
            ),

            severity=payload.severity,
            status="active"
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        return alert

    @staticmethod
    def get_alerts(db: Session):

        return db.query(Alert)\
            .filter(Alert.status.in_(["active", "acknowledged"]))\
            .all()

    @staticmethod
    def update_alert(
        db: Session,
        alert_id,
        payload: AlertUpdate
    ):

        alert = db.query(Alert)\
            .filter(Alert.id == alert_id)\
            .first()

        if not alert:
            return None

        alert.status = payload.status

        if payload.assigned_to:
            alert.assigned_to = payload.assigned_to

        if payload.status == "acknowledged":
            alert.acknowledged_at = datetime.utcnow()

        if payload.status == "resolved":
            alert.resolved_at = datetime.utcnow()

        db.commit()
        db.refresh(alert)

        return alert

    @staticmethod
    def nearby_alerts(
        db: Session,
        latitude: float,
        longitude: float,
        radius_meters: float
    ):

        query = text("""
            SELECT *
            FROM alerts
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude),
                    4326
                )::geography,
                :radius
            )
        """)

        result = db.execute(
            query,
            {
                "longitude": longitude,
                "latitude": latitude,
                "radius": radius_meters
            }
        )

        return result.fetchall()