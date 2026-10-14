from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.user import User
from app.schemas.consultation import ( ConsultationCreate, ConsultationResponse, PatientHistoryItem)
from app.services.consultation_service import ( get_patient_history,read_consultation, write_consultation)
from app.services.email_service import queue_appointment_email
from app.websockets.manager import manager

router = APIRouter(tags=["Consultations and patient history"])


@router.post( "/appointments/{appointment_id}/consultation", response_model=ConsultationResponse,
             dependencies=[Depends(require_roles("doctor"))])
async def create_consultation(appointment_id: int,
                        payload: ConsultationCreate,
                        background_tasks: BackgroundTasks,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> Consultation:
    consultation = write_consultation(db, appointment_id, current_user, payload)
    appointment = ( db.query(Appointment).filter(Appointment.id == appointment_id).first())
    if appointment is not None:
        queue_appointment_email( background_tasks,db,appointment,"completed" )
        await manager.broadcast_queue_update(appointment.doctor_id)
    return consultation


@router.get( "/appointments/{appointment_id}/consultation", response_model=ConsultationResponse)
def get_consultation(appointment_id: int, current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> Consultation:
    return read_consultation(db, appointment_id, current_user)


@router.get("/patients/me/history", response_model=List[PatientHistoryItem], dependencies=[Depends(require_roles("patient"))] )
def patient_history(skip: int = Query(default=0, ge=0),
                    limit: int = Query(default=50, ge=1, le=100),
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> List[dict]:
    return get_patient_history(db, current_user, skip=skip, limit=limit)