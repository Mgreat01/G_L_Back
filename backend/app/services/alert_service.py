from fastapi import HTTPException
from sqlalchemy.orm import Session, load_only
from sqlalchemy import func, select, text
from datetime import datetime
from collections import OrderedDict
import json
import time

from app.models.alert_model import Alert
from app.schemas.alert_schema import AlertCreate, AlertUpdate
from app.utils.gps import create_point
import requests

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping


ADDRESS_CACHE_TTL_SECONDS = 60 * 60 * 24
ADDRESS_CACHE_MAX_SIZE = 4096
_address_cache = OrderedDict()


ALERT_COLUMNS = (
    Alert.id,
    Alert.user_id,
    Alert.encrypted_content,
    Alert.encrypted_key,
    Alert.latitude,
    Alert.longitude,
    func.ST_AsGeoJSON(Alert.location).label("location_geojson"),
    Alert.severity,
    Alert.status,
    Alert.assigned_to,
    Alert.created_at,
    Alert.acknowledged_at,
    Alert.resolved_at,
    Alert.address,
)


def _address_cache_key(lat: float, lon: float):
    return f"{lat:.6f}:{lon:.6f}"


def _get_cached_address(lat: float, lon: float):
    key = _address_cache_key(lat, lon)
    cached = _address_cache.get(key)

    if not cached:
        return None

    address, expires_at = cached

    if expires_at < time.time():
        _address_cache.pop(key, None)
        return None

    _address_cache.move_to_end(key)
    return address


def _set_cached_address(lat: float, lon: float, address: str | None):
    if not address:
        return

    key = _address_cache_key(lat, lon)
    _address_cache[key] = (
        address,
        time.time() + ADDRESS_CACHE_TTL_SECONDS
    )
    _address_cache.move_to_end(key)

    while len(_address_cache) > ADDRESS_CACHE_MAX_SIZE:
        _address_cache.popitem(last=False)


def _location_from_geojson(location_geojson):
    if not location_geojson:
        return None

    if isinstance(location_geojson, dict):
        return location_geojson

    return json.loads(location_geojson)


def serialize_alert_row(row):
    address = row.address or _get_cached_address(row.latitude, row.longitude)

    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "encrypted_content": row.encrypted_content,
        "encrypted_key": row.encrypted_key,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "location": _location_from_geojson(row.location_geojson),
        "severity": row.severity,
        "status": row.status,
        "assigned_to": str(row.assigned_to) if row.assigned_to else None,
        "created_at": row.created_at,
        "acknowledged_at": row.acknowledged_at,
        "resolved_at": row.resolved_at,
        "address": address
    }


def serialize_alert(alert: Alert, resolve_missing_address: bool = False):
    # La lecture des alertes ne doit jamais appeler Nominatim : un GET /alerts
    # pourrait sinon declencher un appel HTTP externe par ligne retournee.
    address = alert.address or _get_cached_address(alert.latitude, alert.longitude)

    if resolve_missing_address and not address and alert.latitude and alert.longitude:
        address = reverse_geocode(alert.latitude, alert.longitude)
        _set_cached_address(alert.latitude, alert.longitude, address)

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
    cached_address = _get_cached_address(lat, lon)

    if cached_address:
        return cached_address

    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1}
    headers = {"User-Agent": "alert-app"}  # obligatoire pour Nominatim

    try:
        response = requests.get(url, params=params, headers=headers, timeout=3)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    if "error" in data:
        return None

    address = data.get("display_name", None)
    _set_cached_address(lat, lon, address)

    return address


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
        db.flush()
        alert_id = alert.id
        db.commit()

        row = db.execute(
            select(*ALERT_COLUMNS).where(Alert.id == alert_id)
        ).first()

        return serialize_alert_row(row)

    @staticmethod
    def resolve_alert_address(alert_id):
        # Resolution volontairement separee des requetes HTTP : Nominatim est
        # externe, lent et rate-limite. On persiste le resultat pour les lectures.
        from app.core.database import SessionLocal

        db = SessionLocal()

        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()

            if not alert or alert.address:
                return

            address = reverse_geocode(alert.latitude, alert.longitude)

            if not address:
                return

            alert.address = address
            db.commit()
        finally:
            db.close()



    @staticmethod
    def get_alerts(
            db: Session,
            current_user,
            skip: int = 0,
            limit: int | None = None
    ):

        role = current_user["role"]

        statement = select(*ALERT_COLUMNS)

        if role == "user":
            statement = statement.where(
                Alert.user_id == current_user["id"]
            )

        statement = statement.order_by(
            Alert.created_at.desc()
        )

        if skip:
            statement = statement.offset(skip)

        if limit is not None:
            statement = statement.limit(limit)

        rows = db.execute(statement).all()

        return [
            serialize_alert_row(row)
            for row in rows
        ]

    @staticmethod
    def get_active_alerts_for_admin(
            db: Session,
            limit: int | None = None
    ):
        # Les notifications initiales representent l'etat a traiter au moment
        # ou l'administrateur ouvre le site, pas l'historique complet.
        statement = select(*ALERT_COLUMNS) \
            .where(Alert.status == "active") \
            .order_by(Alert.created_at.desc())

        if limit is not None:
            statement = statement.limit(limit)

        rows = db.execute(statement).all()

        return [
            serialize_alert_row(row)
            for row in rows
        ]

    @staticmethod
    def update_alert(
            db: Session,
            alert_id,
            payload: AlertUpdate,
            current_user
    ):

        alert = db.query(Alert) \
            .options(
                load_only(
                    Alert.id,
                    Alert.user_id,
                    Alert.severity,
                    Alert.status,
                    Alert.assigned_to,
                    Alert.acknowledged_at,
                    Alert.resolved_at,
                    Alert.address
                )
            ) \
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

        row = db.execute(
            select(*ALERT_COLUMNS).where(Alert.id == alert_id)
        ).first()

        return serialize_alert_row(row)

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
            AND location IS NOT NULL
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
