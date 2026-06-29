from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.models.alert_model import Alert
from app.schemas.alert_schema import AlertCreate, AlertUpdate
from app.utils.gps import create_point
import requests

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping


def serialize_alert(alert: Alert):
    address = reverse_geocode(alert.latitude, alert.longitude) if alert.latitude and alert.longitude else None
    return {
        "id": str(alert.id),
        "user_id": str(alert.user_id),
        "encrypted_content": alert.encrypted_content,
        "encrypted_key": alert.encrypted_key,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "location": mapping(to_shape(alert.location)) if alert.location else None,
        "severity": alert.severity,
        "status": alert.status,
        "assigned_to": str(alert.assigned_to) if alert.assigned_to else None,
        "created_at": alert.created_at,
        "acknowledged_at": alert.acknowledged_at,
        "resolved_at": alert.resolved_at,
        "address": address
    }

def reverse_geocode(lat: float, lon: float):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1}
    headers = {"User-Agent": "alert-app"}  # obligatoire pour Nominatim
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        return None
    data = response.json()
    return data.get("display_name")



class AlertService:

    @staticmethod
    def create_alert(db: Session, payload: AlertCreate, user_id):
        alert = Alert(
            user_id=user_id,
            encrypted_content=payload.encrypted_content,
            encrypted_key=payload.encrypted_key,
            latitude=payload.latitude,
            longitude=payload.longitude,
            location=create_point(payload.longitude, payload.latitude),
            severity=payload.severity,
            status="active"
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        return serialize_alert(alert)

    @staticmethod
    def get_alerts(
            db: Session,
            current_user
    ):

        role = current_user["role"]

        query = db.query(Alert)

        if role == "user":
            query = query.filter(
                Alert.user_id == current_user["id"]
            )

        alerts = query.order_by(
            Alert.created_at.desc()
        ).all()

        return [
            serialize_alert(a)
            for a in alerts
        ]

    @staticmethod
    def update_alert(
            db: Session,
            alert_id,
            payload: AlertUpdate,
            current_user
    ):

        alert = db.query(Alert) \
            .filter(Alert.id == alert_id) \
            .first()

        if not alert:
            raise HTTPException(
                status_code=404,
                detail="Alert not found"
            )

        role = current_user["role"]

        is_owner = str(alert.user_id) == current_user["id"]

        if role not in ["admin", "rescuer"] and not is_owner:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        if payload.status:
            alert.status = payload.status

        if payload.assigned_to:

            if role not in ["admin", "operator"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only operators/admins can assign alerts"
                )

            alert.assigned_to = payload.assigned_to

        if payload.severity:

            if role not in ["admin", "operator"]:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot modify severity"
                )

            alert.severity = payload.severity

        if payload.status == "acknowledged":
            alert.acknowledged_at = datetime.utcnow()

        if payload.status == "resolved":
            alert.resolved_at = datetime.utcnow()

        db.commit()

        db.refresh(alert)

        return serialize_alert(alert)

    @staticmethod
    def nearby_alerts(db: Session, latitude: float, longitude: float, radius_meters: float):
        query = text("""
            SELECT id, user_id, encrypted_content, encrypted_key,
                   latitude, longitude,
                   ST_AsGeoJSON(location) as location,
                   severity, status, assigned_to,
                   created_at, acknowledged_at, resolved_at
            FROM alerts
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                :radius
            )
        """)

        result = db.execute(query, {
            "longitude": longitude,
            "latitude": latitude,
            "radius": radius_meters
        })

        rows = result.fetchall()

        alerts = []
        for row in rows:
            alerts.append({
                "id": str(row.id),
                "user_id": str(row.user_id),
                "encrypted_content": row.encrypted_content,
                "encrypted_key": row.encrypted_key,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "location": row.location,
                "severity": row.severity,
                "status": row.status,
                "assigned_to": str(row.assigned_to) if row.assigned_to else None,
                "created_at": row.created_at,
                "acknowledged_at": row.acknowledged_at,
                "resolved_at": row.resolved_at,
            })

        return alerts
