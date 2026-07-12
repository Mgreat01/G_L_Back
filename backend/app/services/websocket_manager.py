from datetime import datetime
from typing import Any
import asyncio

from fastapi import WebSocket
from starlette.websockets import WebSocketState


WEBSOCKET_SEND_TIMEOUT_SECONDS = 2


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
        self.user_connections: dict[str, list[WebSocket]] = {}
        self.rescuer_connections: dict[str, list[WebSocket]] = {}

    async def connect_admin(self, websocket: WebSocket):
        self.disconnect_admin(websocket)
        await websocket.accept()
        self.admin_connections.append(websocket)

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)

    async def connect_user(self, user_id: str, websocket: WebSocket):
        self.disconnect_user(user_id, websocket)
        await websocket.accept()
        self.user_connections.setdefault(user_id, []).append(websocket)

    def disconnect_user(self, user_id: str, websocket: WebSocket):
        connections = self.user_connections.get(user_id, [])
        if websocket in connections:
            connections.remove(websocket)

        if not connections and user_id in self.user_connections:
            self.user_connections.pop(user_id, None)

    async def connect_rescuer(self, rescuer_id: str, websocket: WebSocket):
        self.disconnect_rescuer(rescuer_id, websocket)
        await websocket.accept()
        self.rescuer_connections.setdefault(rescuer_id, []).append(websocket)

    def disconnect_rescuer(self, rescuer_id: str, websocket: WebSocket):
        connections = self.rescuer_connections.get(rescuer_id, [])
        if websocket in connections:
            connections.remove(websocket)

        if not connections and rescuer_id in self.rescuer_connections:
            self.rescuer_connections.pop(rescuer_id, None)

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

    async def notify_user(self, user_id: str, message: dict):
        connections = list(self.user_connections.get(user_id, []))

        await asyncio.gather(
            *[
                self.send_to_user(user_id, websocket, message)
                for websocket in connections
            ],
            return_exceptions=True
        )

    async def send_to_admin(self, websocket: WebSocket, message: dict):
        if websocket.client_state != WebSocketState.CONNECTED:
            self.disconnect_admin(websocket)
            return False

        try:
            await asyncio.wait_for(
                websocket.send_json(_json_safe(message)),
                timeout=WEBSOCKET_SEND_TIMEOUT_SECONDS
            )
            return True
        except (asyncio.TimeoutError, Exception):
            # Si l'envoi echoue, le client est considere mort et retire du pool.
            self.disconnect_admin(websocket)
            return False

    async def send_to_user(self, user_id: str, websocket: WebSocket, message: dict):
        if websocket.client_state != WebSocketState.CONNECTED:
            self.disconnect_user(user_id, websocket)
            return False

        try:
            await asyncio.wait_for(
                websocket.send_json(_json_safe(message)),
                timeout=WEBSOCKET_SEND_TIMEOUT_SECONDS
            )
            return True
        except (asyncio.TimeoutError, Exception):
            self.disconnect_user(user_id, websocket)
            return False

    async def send_to_rescuer(self, rescuer_id: str, websocket: WebSocket, message: dict):
        if websocket.client_state != WebSocketState.CONNECTED:
            self.disconnect_rescuer(rescuer_id, websocket)
            return False

        try:
            await asyncio.wait_for(
                websocket.send_json(_json_safe(message)),
                timeout=WEBSOCKET_SEND_TIMEOUT_SECONDS
            )
            return True
        except (asyncio.TimeoutError, Exception):
            self.disconnect_rescuer(rescuer_id, websocket)
            return False

    async def notify_rescuer(self, rescuer_id: str, message: dict):
        connections = list(self.rescuer_connections.get(rescuer_id, []))

        await asyncio.gather(
            *[
                self.send_to_rescuer(rescuer_id, websocket, message)
                for websocket in connections
            ],
            return_exceptions=True
        )

    async def send_initial_alerts_to_rescuer(self, websocket: WebSocket, alerts: list[dict]):
        return await self.send_to_rescuer(
            websocket,
            {
                "type": "initial_alerts",
                "data": alerts
            }
        )

    async def notify_rescuer_alert_assigned(self, rescuer_id: str, alert: dict):
        await self.notify_rescuer(rescuer_id, {
            "type": "alert_assigned",
            "data": alert
        })

    async def notify_rescuer_alert_updated(self, rescuer_id: str, alert: dict):
        await self.notify_rescuer(rescuer_id, {
            "type": "alert_updated",
            "data": alert
        })

    async def notify_rescuer_alert_resolved(self, rescuer_id: str, alert: dict):
        await self.notify_rescuer(rescuer_id, {
            "type": "alert_resolved",
            "data": alert
        })

    async def broadcast_to_admins(self, message: dict):
        payload = _json_safe(message)
        connected_websockets = []

        # Iterer sur une copie evite les surprises si une deconnexion modifie la liste.
        for websocket in list(self.admin_connections):
            if websocket.client_state != WebSocketState.CONNECTED:
                self.disconnect_admin(websocket)
                continue

            connected_websockets.append(websocket)

        # Les envois sont paralleles et bornes : un admin lent ne retarde pas les autres.
        await asyncio.gather(
            *[
                self.send_to_admin(websocket, payload)
                for websocket in connected_websockets
            ],
            return_exceptions=True
        )


websocket_manager = WebSocketManager()
