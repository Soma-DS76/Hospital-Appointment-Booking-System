from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.health import HealthStatus
from app.services.health_service import get_health_status

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthStatus, status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)) -> HealthStatus:
    data = get_health_status(db)
    return HealthStatus(**data)


@router.get("/ready", response_model=HealthStatus, status_code=status.HTTP_200_OK)
def readiness_check(db: Session = Depends(get_db)) -> HealthStatus:
    data = get_health_status(db)
    if data["status"] != "ok":
        return HealthStatus(**{**data, "status": "not_ready"})
    return HealthStatus(**data)
