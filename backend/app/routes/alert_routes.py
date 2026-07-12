from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, get_user_from_token
from app.core.permissions import can_view_nearby_alerts
from app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertHistoryResponse,
    RescuerAlertStatusUpdate,
    RescuerDashboardStats
)
from app.services.alert_service import AlertService
from app.services.crypto_service import is_rescue_role, normalize_role
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.services.websocket_manager import websocket_manager

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


@router.post("/", response_model=AlertResponse)
def create_alert(
    alert: AlertCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    created_alert = AlertService.create_alert(
        db,
        alert,
        current_user
    )

    # Le broadcast WebSocket et le geocodage inverse partent apres la reponse :
    # la creation HTTP reste limitee au commit SQL et ne depend pas des admins connectes.
    background_tasks.add_task(
        websocket_manager.notify_admins_new_alert,
        created_alert
    )
    for recipient_key in alert.recipient_keys:
        background_tasks.add_task(
            websocket_manager.notify_user,
            str(recipient_key.recipient_user_id),
            {
                "type": "new_alert",
                "data": created_alert
            }
        )
    background_tasks.add_task(
        AlertService.resolve_alert_address,
        created_alert["id"]
    )

    return created_alert


@router.websocket("/ws/admin")
async def admin_alerts_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    db = SessionLocal()

    try:
        current_user = get_user_from_token(token, db)

        if not current_user or current_user["role"] != "admin":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket_manager.connect_admin(websocket)

        initial_alerts = AlertService.get_active_alerts_for_admin(db)
        initial_sent = await websocket_manager.send_initial_alerts(
            websocket,
            initial_alerts
        )

        if not initial_sent:
            return

        # La boucle garde la connexion vivante et detecte les fermetures client.
        # Les notifications sortantes sont envoyees par websocket_manager.
        while True:
            await websocket.receive_text()
    except (RuntimeError, WebSocketDisconnect):
        websocket_manager.disconnect_admin(websocket)
    finally:
        websocket_manager.disconnect_admin(websocket)
        db.close()


@router.websocket("/ws")
async def legacy_admin_alerts_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    await admin_alerts_websocket(websocket, token)



@router.get("/")
def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return AlertService.get_alerts(
        db,
        current_user,
        skip,
        limit
    )


@router.put("/{alert_id}")
def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    updated_alert = AlertService.update_alert(
        db,
        alert_id,
        payload,
        current_user
    )

    if updated_alert.get("assigned_to"):
        background_tasks.add_task(
            websocket_manager.notify_user,
            updated_alert["assigned_to"],
            {
                "type": "alert_updated",
                "data": updated_alert
            }
        )
        # Also notify rescuer if assigned
        background_tasks.add_task(
            websocket_manager.notify_rescuer_alert_assigned,
            updated_alert["assigned_to"],
            updated_alert
        )

    background_tasks.add_task(
        websocket_manager.broadcast_to_admins,
        {
            "type": "alert_updated",
            "data": updated_alert
        }
    )

    return updated_alert


@router.get("/{alert_id}/history", response_model=list[AlertHistoryResponse])
def get_alert_history(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return AlertService.get_alert_history(
        db,
        alert_id,
        current_user
    )


@router.get("/nearby/")
def nearby_alerts(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(1000, ge=1, le=100000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not can_view_nearby_alerts(current_user):
        return []

    return AlertService.nearby_alerts(
        db,
        latitude,
        longitude,
        radius_meters
    )


@router.websocket("/ws/rescuer")
async def rescuer_alerts_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    db = SessionLocal()

    try:
        current_user = get_user_from_token(token, db)

        if not current_user or not is_rescue_role(normalize_role(current_user["role"])):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        rescuer_id = current_user["id"]
        await websocket_manager.connect_rescuer(rescuer_id, websocket)

        initial_alerts = AlertService.get_assigned_alerts_for_rescuer(db, rescuer_id)
        initial_sent = await websocket_manager.send_initial_alerts_to_rescuer(
            websocket,
            initial_alerts
        )

        if not initial_sent:
            return

        while True:
            await websocket.receive_text()
    except (RuntimeError, WebSocketDisconnect):
        websocket_manager.disconnect_rescuer(rescuer_id, websocket)
    finally:
        websocket_manager.disconnect_rescuer(rescuer_id, websocket)
        db.close()


# Rescuer-specific routes

@router.get("/rescuer/assigned")
def get_assigned_alerts(
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not is_rescue_role(normalize_role(current_user["role"])):
        raise HTTPException(status_code=403, detail="Access denied")

    return AlertService.get_assigned_alerts_for_rescuer(
        db,
        current_user["id"],
        status
    )


@router.put("/{alert_id}/accept")
def accept_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not is_rescue_role(normalize_role(current_user["role"])):
        raise HTTPException(status_code=403, detail="Access denied")

    return AlertService.accept_alert(db, alert_id, current_user)


@router.put("/{alert_id}/start")
def start_intervention(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not is_rescue_role(normalize_role(current_user["role"])):
        raise HTTPException(status_code=403, detail="Access denied")

    return AlertService.start_intervention(db, alert_id, current_user)


@router.put("/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not is_rescue_role(normalize_role(current_user["role"])):
        raise HTTPException(status_code=403, detail="Access denied")

    return AlertService.resolve_alert_by_rescuer(db, alert_id, current_user)


@router.get("/rescuer/dashboard/stats")
def get_rescuer_dashboard_stats(
    latitude: float = Query(None, ge=-90, le=90),
    longitude: float = Query(None, ge=-180, le=180),
    radius_meters: float = Query(5000, ge=1, le=100000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not is_rescue_role(normalize_role(current_user["role"])):
        raise HTTPException(status_code=403, detail="Access denied")

    return AlertService.get_rescuer_dashboard_stats(
        db,
        current_user["id"],
        latitude,
        longitude,
        radius_meters
    )
