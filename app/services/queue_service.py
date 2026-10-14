from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_history import AppointmentHistory
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.queue import QueueSnapshot


def get_queue_snapshot( db: Session, doctor_id: int, user_id: int ) -> QueueSnapshot:
    doctor = ( db.query(Doctor) .filter(Doctor.id == doctor_id, Doctor.is_active.is_(True)).first())
    if doctor is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND,detail="Active doctor not found" )

    today = date.today()
    current = ( db.query(Appointment)
        .filter( Appointment.doctor_id == doctor_id, Appointment.appointment_date == today,
                 Appointment.status == AppointmentStatus.IN_CONSULTATION )
        .order_by(Appointment.token_number)
        .first())

    waiting = (
        db.query(Appointment)
        .filter( Appointment.doctor_id == doctor_id, Appointment.appointment_date == today, Appointment.status == AppointmentStatus.CHECKED_IN )
        .order_by(Appointment.token_number) .all() )

    own_appointment = ( db.query(Appointment)
        .filter( Appointment.doctor_id == doctor_id, Appointment.patient_id == user_id, 
                 Appointment.appointment_date == today, Appointment.status.in_(
                [ AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION ])).first())

    position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None

    if own_appointment is not None:
        if own_appointment.status == AppointmentStatus.IN_CONSULTATION:
            position = 0 
            estimated_wait_minutes = 0
        elif own_appointment.status == AppointmentStatus.CHECKED_IN:
            position = next( ( index + 1 for index, item in enumerate(waiting)
                              if item.id == own_appointment.id ), None )
            if position is not None: 
                ahead = sum( item.token_number < own_appointment.token_number
                    for item in waiting )
                if ( current is not None
                    and current.token_number < own_appointment.token_number ):
                    ahead += 1
                estimated_wait_minutes = ( ahead * doctor.slot_duration_minutes )

    return QueueSnapshot( doctor_id=doctor_id,
                          current_token_number=current.token_number if current else None, 
                          waiting_count=len(waiting),
                          own_token_number=( own_appointment.token_number if own_appointment else None ),
                          position=position, estimated_wait_minutes=estimated_wait_minutes )


def call_next_patient( db: Session, doctor_user: User ) -> Appointment:
    if doctor_user.role != "doctor":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can call the next patient" )

    doctor = ( db.query(Doctor)
        .filter( Doctor.user_id == doctor_user.id, 
                 Doctor.is_active.is_(True))
        .with_for_update()
        .first())
    if doctor is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Active doctor profile not found")

    current = ( db.query(Appointment)
        .filter( Appointment.doctor_id == doctor.id,
                 Appointment.appointment_date == date.today(),
                 Appointment.status == AppointmentStatus.IN_CONSULTATION )
                 .with_for_update()
                 .first())
    if current is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT,
                            detail="Complete the current consultation before calling the next patient" )

    next_appointment = ( db.query(Appointment)
        .filter( Appointment.doctor_id == doctor.id,
                 Appointment.appointment_date == date.today(),
                 Appointment.status == AppointmentStatus.CHECKED_IN )
        .order_by(Appointment.token_number)
        .with_for_update()
        .first())
    if next_appointment is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND,detail="There are no checked-in patients waiting" )

    old_status = next_appointment.status
    next_appointment.status = AppointmentStatus.IN_CONSULTATION
    db.add( AppointmentHistory(
            appointment_id=next_appointment.id,
            old_status=old_status,
            new_status=AppointmentStatus.IN_CONSULTATION,
            changed_by=doctor_user.id ))
    db.commit()
    db.refresh(next_appointment)
    return next_appointment