from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.services.doctor_service import ( create_doctor, deactivate_doctor, get_doctor, list_doctors, update_doctor )

from app.schemas.appointment import AppointmentResponse
from app.services.queue_service import call_next_patient
from app.websockets.manager import manager

from app.deps import get_current_user, require_roles
from app.models.appointment import Appointment
from app.models.user import User

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.post( "", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED,dependencies=[Depends(require_roles("admin"))])
def create( payload: DoctorCreate, db: Session = Depends(get_db)) -> Doctor:
    return create_doctor(db, payload)


@router.get("", response_model=List[DoctorResponse])
def list_all( skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100),
              department_id: Optional[int] = Query(default=None, gt=0),
              specialization: Optional[str] = None, name: Optional[str] = None,
              db: Session = Depends(get_db)) -> List[Doctor]:
    return list_doctors( db, skip=skip, limit=limit, department_id=department_id,
                         specialization=specialization, name=name, active_only=True)


@router.get("/{doctor_id}", response_model=DoctorResponse)
def read_one( doctor_id: int, db: Session = Depends(get_db)) -> Doctor:
    return get_doctor(db, doctor_id, active_only=True)


@router.put("/{doctor_id}",response_model=DoctorResponse,dependencies=[Depends(require_roles("admin"))])
def update( doctor_id: int, payload: DoctorUpdate, db: Session = Depends(get_db)) -> Doctor:
    return update_doctor(db, doctor_id, payload)


@router.delete( "/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT,dependencies=[Depends(require_roles("admin"))])
def deactivate( doctor_id: int, db: Session = Depends(get_db) ) -> Response:
    deactivate_doctor(db, doctor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put( "/me/call-next", response_model=AppointmentResponse, dependencies=[Depends(require_roles("doctor"))])
async def call_next( current_user: User = Depends(get_current_user),db: Session = Depends(get_db)) -> Appointment:
    appointment = call_next_patient(db, current_user)

    await manager.broadcast_queue_update(appointment.doctor_id)
    await manager.send_user_event(
        appointment.patient_id,
        { "event": "your_turn",
         "message": "You are next, please be ready",
         "appointment_id": appointment.id,
         "token_number": appointment.token_number })
    return appointment