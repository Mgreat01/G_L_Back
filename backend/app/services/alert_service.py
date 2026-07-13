from fastapi import HTTPException
from sqlalchemy.orm import Session, load_only
from sqlalchemy import func, or_, select, text
from datetime import datetime
from collections import OrderedDict
import json
import time

from app.models.alert_model import Alert, AlertHistory, AlertRecipientKey
from app.models.user_model import User
from app.schemas.alert_schema import AlertCreate, AlertUpdate, AdminAlertAssignment
from app.services.crypto_service import (
    is_privileged_role,
    is_rescue_role,
    normalize_role
)
from app.core.permissions import (
    can_view_alert,
    can_update_alert,
    can_assign_alert
)
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
    Alert.encryption_algorithm,
    Alert.encrypted_content_nonce,
    Alert.encrypted_content_tag,
    Alert.key_encryption_algorithm,
    Alert.latitude,
    Alert.longitude,
    func.ST_AsGeoJSON(Alert.location).label("location_geojson"),
    Alert.severity,
    Alert.status,
    Alert.assigned_to,
    Alert.created_at,
    Alert.acknowledged_at,
    Alert.assigned_at,
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


def serialize_recipient_key(recipient_key):
    return {
        "recipient_user_id": str(recipient_key.recipient_user_id),
        "encrypted_key": recipient_key.encrypted_key,
        "key_encryption_algorithm": recipient_key.key_encryption_algorithm,
        "created_at": recipient_key.created_at
    }


def serialize_alert_row(row, recipient_keys: list | None = None):
    address = row.address or _get_cached_address(row.latitude, row.longitude)

    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "encrypted_content": row.encrypted_content,
        "encrypted_key": row.encrypted_key,
        "encryption_algorithm": row.encryption_algorithm,
        "encrypted_content_nonce": row.encrypted_content_nonce,
        "encrypted_content_tag": row.encrypted_content_tag,
        "key_encryption_algorithm": row.key_encryption_algorithm,
        "recipient_keys": recipient_keys or [],
        "latitude": row.latitude,
        "longitude": row.longitude,
        "location": _location_from_geojson(row.location_geojson),
        "severity": row.severity,
        "status": row.status,
        "assigned_to": str(row.assigned_to) if row.assigned_to else None,
        "created_at": row.created_at,
        "acknowledged_at": row.acknowledged_at,
        "assigned_at": row.assigned_at,
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
        "encryption_algorithm": alert.encryption_algorithm,
        "encrypted_content_nonce": alert.encrypted_content_nonce,
        "encrypted_content_tag": alert.encrypted_content_tag,
        "key_encryption_algorithm": alert.key_encryption_algorithm,
        "recipient_keys": [
            serialize_recipient_key(item)
            for item in getattr(alert, "recipient_keys", [])
        ],
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "location": mapping(to_shape(alert.location)) if alert.location else None,
        "severity": alert.severity,
        "status": alert.status,
        "assigned_to": str(alert.assigned_to) if alert.assigned_to else None,
        "created_at": alert.created_at,
        "acknowledged_at": alert.acknowledged_at,
        "assigned_at": alert.assigned_at,
        "resolved_at": alert.resolved_at,
        "address": address
    }


def _user_can_access_alert(current_user, alert: Alert):
    role = normalize_role(current_user["role"])
    user_id = current_user["id"]

    if role in ["admin", "operator"]:
        return True

    if str(alert.user_id) == user_id:
        return True

    if is_rescue_role(role) and str(alert.assigned_to) == user_id:
        return True

    return False


def _recipient_keys_for_user(db: Session, alert_id, current_user):
    statement = select(AlertRecipientKey).where(AlertRecipientKey.alert_id == alert_id)

    if normalize_role(current_user["role"]) not in ["admin", "operator"]:
        statement = statement.where(
            AlertRecipientKey.recipient_user_id == current_user["id"]
        )

    keys = db.execute(statement).scalars().all()
    return [serialize_recipient_key(key) for key in keys]


def _add_alert_history(
    db: Session,
    alert: Alert,
    actor_user_id,
    action: str,
    previous_status: str | None = None,
    previous_assigned_to=None
):
    db.add(
        AlertHistory(
            alert_id=alert.id,
            actor_user_id=actor_user_id,
            action=action,
            previous_status=previous_status,
            new_status=alert.status,
            previous_assigned_to=previous_assigned_to,
            new_assigned_to=alert.assigned_to
        )
    )


def _get_active_rescuer(db: Session, rescuer_id):
    """Retourne un secouriste actif ou refuse une affectation invalide."""
    rescuer = db.query(User).filter(User.id == rescuer_id).first()

    if (
        not rescuer
        or not rescuer.is_active
        or not rescuer.email_verified
        or not is_rescue_role(rescuer.role)
    ):
        raise HTTPException(
            status_code=422,
            detail="The assignee must be an active, verified rescuer"
        )

    return rescuer


def _ensure_assignable_alert(alert: Alert):
    if alert.status in {"resolved", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="A resolved or cancelled alert cannot be assigned"
        )


def _add_recipient_key_if_needed(
    db: Session,
    alert: Alert,
    rescuer_id,
    recipient_key
):
    existing_key = db.query(AlertRecipientKey).filter(
        AlertRecipientKey.alert_id == alert.id,
        AlertRecipientKey.recipient_user_id == rescuer_id
    ).first()

    if existing_key:
        return

    if not recipient_key:
        raise HTTPException(
            status_code=422,
            detail=(
                "An encrypted recipient key for the assigned rescuer is required "
                "because this alert is end-to-end encrypted"
            )
        )

    if recipient_key.recipient_user_id != rescuer_id:
        raise HTTPException(
            status_code=422,
            detail="recipient_key.recipient_user_id must match rescuer_id"
        )

    db.add(AlertRecipientKey(
        alert_id=alert.id,
        recipient_user_id=rescuer_id,
        encrypted_key=recipient_key.encrypted_key,
        key_encryption_algorithm=recipient_key.key_encryption_algorithm
    ))

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
    def create_alert(db: Session, payload: AlertCreate, current_user):
        alert = Alert(
            user_id=current_user["id"],
            encrypted_content=payload.encrypted_content,
            encrypted_key=payload.encrypted_key,
            encryption_algorithm=payload.encryption_algorithm,
            encrypted_content_nonce=payload.encrypted_content_nonce,
            encrypted_content_tag=payload.encrypted_content_tag,
            key_encryption_algorithm=payload.key_encryption_algorithm,
            latitude=payload.latitude,
            longitude=payload.longitude,
            location=create_point(payload.longitude, payload.latitude),
            severity=payload.severity,
            status="active"
        )

        db.add(alert)
        db.flush()

        recipient_ids = set()
        for key_payload in payload.recipient_keys:
            recipient_id = str(key_payload.recipient_user_id)
            if recipient_id in recipient_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate recipient key"
                )
            recipient_ids.add(recipient_id)

        if recipient_ids:
            valid_recipients = db.execute(
                select(User.id).where(
                    User.id.in_(list(recipient_ids)),
                    User.is_active.is_(True),
                    User.public_key.isnot(None)
                )
            ).scalars().all()
            valid_recipient_ids = {str(user_id) for user_id in valid_recipients}

            if valid_recipient_ids != recipient_ids:
                raise HTTPException(
                    status_code=400,
                    detail="All alert recipients must be active users with public keys"
                )

        for key_payload in payload.recipient_keys:
            db.add(
                AlertRecipientKey(
                    alert_id=alert.id,
                    recipient_user_id=key_payload.recipient_user_id,
                    encrypted_key=key_payload.encrypted_key,
                    key_encryption_algorithm=key_payload.key_encryption_algorithm
                )
            )

        _add_alert_history(
            db,
            alert,
            current_user["id"],
            "created"
        )

        notification_targets = db.execute(
            select(User.id).where(
                User.is_active.is_(True),
                or_(
                    User.role.in_(["admin", "operator"]),
                    User.id.in_(list(recipient_ids)) if recipient_ids else False
                )
            )
        ).scalars().all()



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

        role = normalize_role(current_user["role"])
        user_id = current_user["id"]

        statement = select(*ALERT_COLUMNS)

        if role == "user":
            statement = statement.where(
                Alert.user_id == user_id
            )
        elif is_rescue_role(role):
            statement = statement.outerjoin(
                AlertRecipientKey,
                AlertRecipientKey.alert_id == Alert.id
            ).where(
                or_(
                    Alert.assigned_to == user_id,
                    AlertRecipientKey.recipient_user_id == user_id
                )
            ).distinct()

        statement = statement.order_by(
            Alert.created_at.desc()
        )

        if skip:
            statement = statement.offset(skip)

        if limit is not None:
            statement = statement.limit(limit)

        rows = db.execute(statement).all()

        return [
            serialize_alert_row(
                row,
                _recipient_keys_for_user(db, row.id, current_user)
            )
            for row in rows
        ]

    @staticmethod
    def get_active_alerts_for_admin(
            db: Session,
            limit: int | None = None
    ):

        statement = select(*ALERT_COLUMNS) \
            .where(Alert.status.in_(["active", "acknowledged", "assigned"])) \
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
                    Alert.assigned_at,
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

        role = normalize_role(current_user["role"])

        is_owner = str(alert.user_id) == current_user["id"]

        if not _user_can_access_alert(current_user, alert):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        previous_status = alert.status
        previous_assigned_to = alert.assigned_to

        if payload.status:
            if is_owner and payload.status != "cancelled" and role == "user":
                raise HTTPException(
                    status_code=403,
                    detail="Users can only cancel their own alerts"
                )

            if is_rescue_role(role) and str(alert.assigned_to) != current_user["id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only the assigned rescue team can update status"
                )

            alert.status = payload.status

        if payload.assigned_to:

            if not is_privileged_role(role):
                raise HTTPException(
                    status_code=403,
                    detail="Only operators/admins can assign alerts"
                )

            _get_active_rescuer(db, payload.assigned_to)
            _ensure_assignable_alert(alert)
            _add_recipient_key_if_needed(db, alert, payload.assigned_to, None)
            alert.assigned_to = payload.assigned_to
            alert.assigned_at = datetime.utcnow()
            if not payload.status:
                alert.status = "assigned"



        if payload.severity:

            if not is_privileged_role(role):
                raise HTTPException(
                    status_code=403,
                    detail="Cannot modify severity"
                )

            alert.severity = payload.severity

        if payload.status == "acknowledged":
            alert.acknowledged_at = datetime.utcnow()

        if payload.status == "resolved":
            alert.resolved_at = datetime.utcnow()

        if payload.status or payload.assigned_to or payload.severity:
            _add_alert_history(
                db,
                alert,
                current_user["id"],
                "updated",
                previous_status,
                previous_assigned_to
            )

        db.commit()

        row = db.execute(
            select(*ALERT_COLUMNS).where(Alert.id == alert_id)
        ).first()

        return serialize_alert_row(
            row,
            _recipient_keys_for_user(db, row.id, current_user)
        )

    @staticmethod
    def assign_alert(
            db: Session,
            alert_id: str,
            payload: AdminAlertAssignment,
            current_user: dict
    ):
        """Affecte une alerte à un secouriste depuis la console d'administration."""
        if not is_privileged_role(current_user["role"]):
            raise HTTPException(status_code=403, detail="Only operators/admins can assign alerts")

        alert = db.query(Alert).filter(Alert.id == alert_id).with_for_update().first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        _ensure_assignable_alert(alert)
        _get_active_rescuer(db, payload.rescuer_id)

        previous_status = alert.status
        previous_assigned_to = alert.assigned_to
        _add_recipient_key_if_needed(db, alert, payload.rescuer_id, payload.recipient_key)

        alert.assigned_to = payload.rescuer_id
        alert.assigned_at = datetime.utcnow()
        alert.status = "assigned"

        _add_alert_history(
            db, alert, current_user["id"], "assigned_by_admin",
            previous_status, previous_assigned_to
        )
        db.commit()

        row = db.execute(select(*ALERT_COLUMNS).where(Alert.id == alert.id)).first()
        return serialize_alert_row(row, _recipient_keys_for_user(db, row.id, current_user))

    @staticmethod
    def claim_alert(db: Session, alert_id: str, current_user: dict):
        """Permet à un secouriste de prendre lui-même une alerte disponible."""
        if not is_rescue_role(current_user["role"]):
            raise HTTPException(status_code=403, detail="Access denied")

        if not current_user.get("email_verified"):
            raise HTTPException(
                status_code=403,
                detail="Only verified rescuers can self-assign alerts"
            )

        alert = db.query(Alert).filter(Alert.id == alert_id).with_for_update().first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if alert.status != "active" or alert.assigned_to is not None:
            raise HTTPException(
                status_code=409,
                detail="This alert is no longer available for self-assignment"
            )

        # Un secouriste ne possède pas la clé privée d'un autre destinataire :
        # il ne peut donc prendre que les alertes dont une clé lui a été remise.
        # has_recipient_key = db.query(AlertRecipientKey.id).filter(
        #     AlertRecipientKey.alert_id == alert.id,
        #     AlertRecipientKey.recipient_user_id == current_user["id"]
        # ).first()
        # if not has_recipient_key:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="This rescuer has no decryption key for this alert"
        #     )

        previous_status = alert.status
        alert.assigned_to = current_user["id"]
        alert.assigned_at = datetime.utcnow()
        alert.status = "assigned"

        _add_alert_history(
            db, alert, current_user["id"], "claimed_by_rescuer",
            previous_status, None
        )
        db.commit()

        row = db.execute(select(*ALERT_COLUMNS).where(Alert.id == alert.id)).first()
        return serialize_alert_row(row, _recipient_keys_for_user(db, row.id, current_user))

    @staticmethod
    def get_alert_history(db: Session, alert_id: str, current_user):
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if not _user_can_access_alert(current_user, alert):
            raise HTTPException(status_code=403, detail="Access denied")

        return db.query(AlertHistory).filter(
            AlertHistory.alert_id == alert_id
        ).order_by(AlertHistory.created_at.desc()).all()

    @staticmethod
    def nearby_alerts(db: Session, latitude: float, longitude: float, radius_meters: float):
        query = text("""
            SELECT id, user_id, encrypted_content, encrypted_key,
                   latitude, longitude,
                   ST_AsGeoJSON(location) as location,
                   severity, status, assigned_to,
                   created_at, acknowledged_at, resolved_at,
                   ST_Distance(
                       location::geography,
                       ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
                   ) as distance_meters
            FROM alerts
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                :radius
            )
            AND location IS NOT NULL
            ORDER BY distance_meters ASC
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
                "distance_meters": row.distance_meters
            })

        return alerts

    @staticmethod
    def get_assigned_alerts_for_rescuer(db: Session, rescuer_id: str, status_filter: str = None):
        """Récupère les alertes assignées à un rescuer avec filtre optionnel sur le statut"""
        statement = select(*ALERT_COLUMNS).where(
            Alert.assigned_to == rescuer_id
        )

        if status_filter:
            statement = statement.where(Alert.status == status_filter)

        statement = statement.order_by(Alert.created_at.desc())

        rows = db.execute(statement).all()

        return [
            serialize_alert_row(
                row,
                _recipient_keys_for_user(db, row.id, {
                    "id": str(rescuer_id),
                    "role": "rescuer"
                })
            )
            for row in rows
        ]

    @staticmethod
    def accept_alert(db: Session, alert_id: str, current_user: dict):
        """Rescuer accepte une alerte (status -> acknowledged)"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if not can_update_alert(current_user, alert, "acknowledged"):
            raise HTTPException(
                status_code=403,
                detail="Only assigned rescuer can accept alert"
            )

        previous_status = alert.status
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()

        _add_alert_history(
            db,
            alert,
            current_user["id"],
            "accepted_by_rescuer",
            previous_status,
            alert.assigned_to
        )

        db.commit()

        row = db.execute(
            select(*ALERT_COLUMNS).where(Alert.id == alert_id)
        ).first()

        return serialize_alert_row(row, _recipient_keys_for_user(db, row.id, current_user))

    @staticmethod
    def start_intervention(db: Session, alert_id: str, current_user: dict):
        """Rescuer commence une intervention (status -> assigned)"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if not can_update_alert(current_user, alert, "assigned"):
            raise HTTPException(
                status_code=403,
                detail="Only assigned rescuer can start intervention"
            )

        previous_status = alert.status
        alert.status = "assigned"
        alert.assigned_at = datetime.utcnow()

        _add_alert_history(
            db,
            alert,
            current_user["id"],
            "started_intervention",
            previous_status,
            alert.assigned_to
        )

        db.commit()

        row = db.execute(
            select(*ALERT_COLUMNS).where(Alert.id == alert_id)
        ).first()

        return serialize_alert_row(row, _recipient_keys_for_user(db, row.id, current_user))

    @staticmethod
    def resolve_alert_by_rescuer(db: Session, alert_id: str, current_user: dict):
        """Rescuer résout une alerte (status -> resolved)"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if not can_update_alert(current_user, alert, "resolved"):
            raise HTTPException(
                status_code=403,
                detail="Only assigned rescuer can resolve alert"
            )

        previous_status = alert.status
        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()

        _add_alert_history(
            db,
            alert,
            current_user["id"],
            "resolved",
            previous_status,
            alert.assigned_to
        )

        db.commit()

        row = db.execute(
            select(*ALERT_COLUMNS).where(Alert.id == alert_id)
        ).first()

        return serialize_alert_row(row, _recipient_keys_for_user(db, row.id, current_user))

    @staticmethod
    def get_rescuer_dashboard_stats(db: Session, rescuer_id: str, latitude: float = None, longitude: float = None, radius_meters: float = 5000):
        """Calcule les statistiques pour le dashboard rescuer"""
        # Alertes assignées
        assigned_alerts = db.query(Alert).filter(
            Alert.assigned_to == rescuer_id
        ).all()

        total_assigned = len(assigned_alerts)
        active_count = sum(1 for a in assigned_alerts if a.status == "active")
        acknowledged_count = sum(1 for a in assigned_alerts if a.status == "acknowledged")
        assigned_count = sum(1 for a in assigned_alerts if a.status == "assigned")
        resolved_count = sum(1 for a in assigned_alerts if a.status == "resolved")

        # Alertes nearby
        nearby_count = 0
        if latitude is not None and longitude is not None:
            query = text("""
                SELECT COUNT(*) as count
                FROM alerts
                WHERE ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                    :radius
                )
                AND location IS NOT NULL
                AND status IN ('active', 'acknowledged')
            """)
            result = db.execute(query, {
                "longitude": longitude,
                "latitude": latitude,
                "radius": radius_meters
            })
            nearby_count = result.fetchone().count

        return {
            "total_assigned": total_assigned,
            "active_count": active_count,
            "acknowledged_count": acknowledged_count,
            "assigned_count": assigned_count,
            "resolved_count": resolved_count,
            "nearby_count": nearby_count
        }
