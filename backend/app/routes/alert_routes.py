from fastapi import APIRouter, Depends, Query, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import ALGORITHM, SECRET_KEY
from app.models.user_model import User
from app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse
)
from app.services.alert_service import AlertService
from app.core.security import get_current_user
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


def get_websocket_user(token: str, db: Session):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            return None

        user = db.query(User)\
            .filter(User.id == user_id)\
            .first()

        if not user:
            return None

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "username": user.username
        }

    except JWTError:
        return None


@router.websocket("/ws/admin")
async def admin_alerts_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    db = SessionLocal()
    current_user = get_websocket_user(token, db)

    if not current_user or current_user["role"] != "admin":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        db.close()
        return

    await websocket_manager.connect_admin(websocket)

    try:
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
