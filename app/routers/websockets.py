from typing import Any, Dict
from pathlib import Path

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.database import SessionLocal
from app.models.doctor import Doctor
from app.models.user import User
from app.services.queue_service import get_queue_snapshot
from app.websockets.manager import manager

router = APIRouter()


@router.get("/queue-test", include_in_schema=False)
def queue_test_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "queue_test.html"
    return FileResponse(page_path, media_type="text/html")


def _authenticate(token: str, db: Session) -> User:
    try:
        payload: Dict[str, Any] = decode_token(token)
    except jwt.InvalidTokenError:
        raise ValueError("Invalid access token")

    subject = payload.get("sub")
    if payload.get("type") != "access" or not isinstance(subject, str):
        raise ValueError("Invalid access token")

    try:
        user_id = int(subject)
    except ValueError:
        raise ValueError("Invalid access token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise ValueError("Invalid access token")

    return user


@router.websocket("/ws/queue/{doctor_id}")
async def doctor_queue( websocket: WebSocket,doctor_id: int,token: str = Query(...)) -> None:
    db = SessionLocal()
    try:
        try:
            user = _authenticate(token, db)
        except ValueError:
            await websocket.close(code=4401)
            return

        doctor = ( db.query(Doctor) .filter(Doctor.id == doctor_id, Doctor.is_active.is_(True)).first())
        if doctor is None:
            await websocket.close(code=4404)
            return

        if user.role == "doctor" and doctor.user_id != user.id:
            await websocket.close(code=4403)
            return
        if user.role not in ("doctor", "patient", "admin"):
            await websocket.close(code=4403)
            return

        user_id = user.id
    finally:
        db.close()

    await manager.connect_queue(websocket, doctor_id, user_id)
    try:
        db = SessionLocal()
        try:
            snapshot = get_queue_snapshot(db, doctor_id, user_id)
            await websocket.send_json(snapshot.model_dump(mode="json"))
        finally:
            db.close()

        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/notifications")
async def personal_notifications( websocket: WebSocket,token: str = Query(...)) -> None:
    db = SessionLocal()
    try:
        try:
            user = _authenticate(token, db)
        except ValueError:
            await websocket.close(code=4401)
            return
        user_id = user.id
    finally:
        db.close()

    await manager.connect_user(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        manager.disconnect(websocket)