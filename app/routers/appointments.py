from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User
from app.schemas.appointment import ( AppointmentCreate, AppointmentReschedule, AppointmentResponse)
from app.services.appointment_service import ( book_appointment, cancel_appointment, check_in_appointment,
                                               get_appointment, list_appointments, reschedule_appointment )
from app.services.email_service import queue_appointment_email
from app.websockets.manager import manager

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post( "", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED )
async def create( payload: AppointmentCreate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Appointment:
    appointment = book_appointment(db, current_user, payload)
    queue_appointment_email(background_tasks, db, appointment, "booked")
    await manager.broadcast_queue_update(appointment.doctor_id)
    await manager.send_user_event(
        appointment.patient_id,
        {"event": "appointment_booked", "appointment_id": appointment.id},
    )
    return appointment


@router.get("", response_model=List[AppointmentResponse])
def list_all( skip: int = Query(default=0, ge=0), 
              limit: int = Query(default=50, ge=1, le=100),
              appointment_status: Optional[AppointmentStatus] = Query( default=None,alias="status"),
              doctor_id: Optional[int] = Query(default=None, gt=0),
              start_date: Optional[date] = None,
              end_date: Optional[date] = None,
              appointment_number: Optional[str] = None,
              current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> List[Appointment]:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="end_date must be on or after start_date")

    return list_appointments(db,current_user,skip=skip,limit=limit,
                             appointment_status=appointment_status,doctor_id=doctor_id,
                             start_date=start_date,end_date=end_date,
                             appointment_number=appointment_number)


@router.put( "/{appointment_id}/reschedule", response_model=AppointmentResponse )
async def reschedule( appointment_id: int, payload: AppointmentReschedule,background_tasks: BackgroundTasks,
               current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Appointment:
    appointment = reschedule_appointment( db, current_user, appointment_id, payload )
    queue_appointment_email( background_tasks, db, appointment, "rescheduled" )
    await manager.broadcast_queue_update(appointment.doctor_id)
    await manager.send_user_event(
        appointment.patient_id,
        {"event": "appointment_rescheduled", "appointment_id": appointment.id},
    )
    return appointment


@router.put( "/{appointment_id}/cancel", response_model=AppointmentResponse )
async def cancel( appointment_id: int, background_tasks: BackgroundTasks,current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db)) -> Appointment:
    appointment = cancel_appointment(db, current_user, appointment_id)
    queue_appointment_email( background_tasks, db, appointment,"cancelled")
    await manager.broadcast_queue_update(appointment.doctor_id)
    await manager.send_user_event(
        appointment.patient_id,
        {"event": "appointment_cancelled", "appointment_id": appointment.id})
    return appointment


@router.put( "/{appointment_id}/check-in", response_model=AppointmentResponse, dependencies=[Depends(require_roles("admin"))])
async def check_in( appointment_id: int,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)) -> Appointment:
    appointment = check_in_appointment(db, appointment_id, current_user.id)
    await manager.broadcast_queue_update(appointment.doctor_id)
    return appointment


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def read_one( appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Appointment:
    return get_appointment(db, current_user, appointment_id)