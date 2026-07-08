from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, get_user_from_token
from app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertHistoryResponse
)
from app.services.alert_service import AlertService
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
    if current_user["role"] not in ["admin", "operator", "rescuer", "rescue_team"]:
        return []

    return AlertService.nearby_alerts(
        db,
        latitude,
        longitude,
        radius_meters
    )
