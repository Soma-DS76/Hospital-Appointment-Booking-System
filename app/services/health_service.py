import os
from typing import Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def get_health_status(db: Session) -> Dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "error"

    uploads_dir = settings.UPLOAD_DIR
    try:
        os.makedirs(uploads_dir, exist_ok=True)
        upload_status = "ok"
    except Exception:
        upload_status = "error"

    return { "status": "ok" if database_status == "ok" and upload_status == "ok" else "degraded",
              "database": database_status,
              "uploads_dir": upload_status,
              "environment": settings.ENVIRONMENT }
