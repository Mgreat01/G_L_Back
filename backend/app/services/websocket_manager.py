from datetime import datetime
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


def _json_safe(value: Any):
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


class WebSocketManager:

    def __init__(self):
        self.admin_connections: list[WebSocket] = []

    async def connect_admin(self, websocket: WebSocket):
        self.disconnect_admin(websocket)
        await websocket.accept()
        self.admin_connections.append(websocket)

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)

    async def send_initial_alerts(self, websocket: WebSocket, alerts: list[dict]):
        # Une connexion WebSocket ne rejoue pas naturellement les messages rates.
        # On envoie donc l'etat courant juste apres l'acceptation du socket admin.
        return await self.send_to_admin(websocket, {
            "type": "initial_alerts",
            "data": alerts
        })

    async def notify_admins_new_alert(self, alert: dict):
        await self.broadcast_to_admins({
            "type": "new_alert",
            "data": alert
        })

    async def send_to_admin(self, websocket: WebSocket, message: dict):
        if websocket.client_state != WebSocketState.CONNECTED:
            self.disconnect_admin(websocket)
            return False

        try:
            await websocket.send_json(_json_safe(message))
            return True
        except Exception:
            # Si l'envoi echoue, le client est considere mort et retire du pool.
            self.disconnect_admin(websocket)
            return False

    async def broadcast_to_admins(self, message: dict):
        disconnected_websockets = []
        payload = _json_safe(message)

        # Iterer sur une copie evite les surprises si une deconnexion modifie la liste.
        for websocket in list(self.admin_connections):
            if websocket.client_state != WebSocketState.CONNECTED:
                disconnected_websockets.append(websocket)
                continue

            try:
                await websocket.send_json(payload)
            except Exception:
                disconnected_websockets.append(websocket)

        for websocket in disconnected_websockets:
            self.disconnect_admin(websocket)


websocket_manager = WebSocketManager()
