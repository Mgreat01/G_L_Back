from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, get_user_from_token
from app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse
)
from app.services.alert_service import AlertService
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.services.websocket_manager import websocket_manager

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


@router.post("/", response_model=AlertResponse)
async def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    created_alert = AlertService.create_alert(
        db,
        alert,
        current_user["id"]
    )

    await websocket_manager.notify_admins_new_alert(created_alert)

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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return AlertService.get_alerts(
        db,
        current_user
    )


@router.put("/{alert_id}")
def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return AlertService.update_alert(
        db,
        alert_id,
        payload,
        current_user
    )
