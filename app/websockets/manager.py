import asyncio
import logging
from concurrent.futures import Future
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.queue_connections: Dict[int, Dict[WebSocket, int]] = {}
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        self.connection_loops: Dict[WebSocket, asyncio.AbstractEventLoop] = {}

    async def connect_queue(
        self,
        websocket: WebSocket,
        doctor_id: int,
        user_id: int,
    ) -> None:
        await websocket.accept()
        self.queue_connections.setdefault(doctor_id, {})[websocket] = user_id
        self.connection_loops[websocket] = asyncio.get_running_loop()

    async def connect_user(
        self,
        websocket: WebSocket,
        user_id: int,
    ) -> None:
        await websocket.accept()
        self.user_connections.setdefault(user_id, set()).add(websocket)
        self.connection_loops[websocket] = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket) -> None:
        self.connection_loops.pop(websocket, None)
        for doctor_id, connections in list(self.queue_connections.items()):
            connections.pop(websocket, None)
            if not connections:
                self.queue_connections.pop(doctor_id, None)

        for user_id, connections in list(self.user_connections.items()):
            connections.discard(websocket)
            if not connections:
                self.user_connections.pop(user_id, None)

    async def send_user_event(self, user_id: int, event: dict) -> None:
        for websocket in list(self.user_connections.get(user_id, set())):
            try:
                await websocket.send_json(event)
            except (WebSocketDisconnect, RuntimeError, OSError):
                self.disconnect(websocket)

    async def broadcast_queue_update(self, doctor_id: int) -> None:
        from app.database import SessionLocal
        from app.services.queue_service import get_queue_snapshot

        connections = self.queue_connections.get(doctor_id, {})
        for websocket, user_id in list(connections.items()):
            db = SessionLocal()
            try:
                snapshot = get_queue_snapshot(db, doctor_id, user_id)
                await websocket.send_json(snapshot.model_dump(mode="json"))
            except (WebSocketDisconnect, RuntimeError, OSError):
                self.disconnect(websocket)
            except Exception:
                logger.exception(
                    "Could not broadcast queue update for doctor %s to a connected user",
                    doctor_id,
                )
            finally:
                db.close()

    def broadcast_queue_update_threadsafe(self, doctor_id: int) -> None:
        loops = set(self.connection_loops.values())
        for loop in loops:
            if loop.is_closed() or not loop.is_running():
                continue
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast_queue_update(doctor_id),
                loop,
            )
            future.add_done_callback(self._log_broadcast_failure)

    @staticmethod
    def _log_broadcast_failure(future: Future) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Queue update broadcast failed")


manager = ConnectionManager()