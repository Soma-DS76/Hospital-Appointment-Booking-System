from datetime import date, datetime, time, timedelta
from typing import List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule
from app.services.schedule_service import get_available_slots
from app.models.appointment_history import AppointmentHistory


ACTIVE_STATUSES = ( AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION )


def _renumber_active_appointments(
    db: Session,
    doctor_id: int,
    appointment_date: date,
) -> None:
    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Appointment.slot_time, Appointment.id)
        .with_for_update()
        .all()
    )
    for token_number, appointment in enumerate(appointments, start=1):
        appointment.token_number = token_number


def book_appointment( db: Session, patient: User, data: AppointmentCreate ) -> Appointment:
    if patient.role != "patient":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can book appointments" )

    db.query(User.id).filter(User.id == patient.id).with_for_update().first()

    today = date.today()
    if data.appointment_date <= today:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="Appointments must be booked for a future date" )
    if data.appointment_date > today + timedelta(days=30):
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Appointments can be booked at most 30 days in advance" )

    # Serialize booking attempts for this doctor to prevent concurrent slot conflicts.
    doctor = ( db.query(Doctor) .filter( Doctor.id == data.doctor_id, Doctor.is_active.is_(True) )
              .with_for_update() .first() )
    if doctor is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Active doctor not found" )

    slot_datetime = datetime.combine(data.appointment_date, data.slot_time)
    if slot_datetime <= datetime.now():
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="The selected appointment slot is in the past" )

    available_slots = get_available_slots( db, doctor.id, data.appointment_date )
    if data.slot_time not in available_slots:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="The selected slot is unavailable" )

    patient_same_time = (
        db.query(Appointment.id)
        .filter( Appointment.patient_id == patient.id,
                 Appointment.appointment_date == data.appointment_date, 
                 Appointment.slot_time == data.slot_time, 
                 Appointment.status.in_(ACTIVE_STATUSES)) .first() )
    if patient_same_time is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="You already have an appointment at this date and time" )

    patient_same_doctor_day = ( db.query(Appointment.id) 
                               .filter( Appointment.patient_id == patient.id,
                                        Appointment.doctor_id == doctor.id,
                                        Appointment.appointment_date == data.appointment_date,
                                        Appointment.status.in_(ACTIVE_STATUSES) ) .first() )
    if patient_same_doctor_day is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="You can book only one appointment with this doctor per day" )

    last_token = ( db.query(Appointment.token_number)
                     .filter( Appointment.doctor_id == doctor.id,Appointment.appointment_date == data.appointment_date )
                     .order_by(Appointment.token_number.desc())
                     .with_for_update()
                     .first())
    token_number = (last_token[0] if last_token else 0) + 1

    appointment = Appointment(
        appointment_number=( f"APT-{data.appointment_date:%Y%m%d}-{uuid4().hex[:8].upper()}"
        ), patient_id=patient.id, doctor_id=doctor.id,
        appointment_date=data.appointment_date, slot_time=data.slot_time,
        token_number=token_number, reason=data.reason, status=AppointmentStatus.BOOKED, consultation_fee=doctor.consultation_fee )
    db.add(appointment)

    try:
        db.flush()
        _renumber_active_appointments(db, doctor.id, data.appointment_date)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The appointment conflicts with an existing booking",
        )

    db.refresh(appointment)
    return appointment


def list_appointments( db: Session, current_user: User, skip: int = 0, limit: int = 50, appointment_status: Optional[AppointmentStatus] = None,
    doctor_id: Optional[int] = None, start_date: Optional[date] = None, 
    end_date: Optional[date] = None, appointment_number: Optional[str] = None ) -> List[Appointment]:
    query = db.query(Appointment)

    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        doctor = ( db.query(Doctor) .filter(Doctor.user_id == current_user.id) .first())
        if doctor is None:
            return []
        query = query.filter(Appointment.doctor_id == doctor.id)
    elif current_user.role != "admin":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,detail="You do not have permission to view appointments")

    if appointment_status is not None:
        query = query.filter(Appointment.status == appointment_status)
    if doctor_id is not None:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if start_date is not None:
        query = query.filter(Appointment.appointment_date >= start_date)
    if end_date is not None:
        query = query.filter(Appointment.appointment_date <= end_date)
    if appointment_number:
        query = query.filter( Appointment.appointment_number == appointment_number)

    return ( query.order_by( Appointment.appointment_date, Appointment.slot_time )
        .offset(skip) .limit(limit) .all() )


def get_appointment( db: Session, current_user: User, appointment_id: int ) -> Appointment:
    appointment = ( db.query(Appointment) .filter(Appointment.id == appointment_id) .first())
    if appointment is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found" )

    if current_user.role == "patient":
        allowed = appointment.patient_id == current_user.id
    elif current_user.role == "doctor":
        doctor = ( db.query(Doctor) .filter(Doctor.user_id == current_user.id) 
                  .first())
        allowed = doctor is not None and appointment.doctor_id == doctor.id
    else:
        allowed = current_user.role == "admin"

    if not allowed:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You do not have permission to view this appointment" )

    return appointment


def _get_patient_appointment( db: Session, patient: User, appointment_id: int ) -> Appointment:
    appointment = ( db.query(Appointment) .filter(Appointment.id == appointment_id) .with_for_update().first())

    if appointment is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND,detail="Appointment not found" )

    if patient.role != "patient" or appointment.patient_id != patient.id:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="You can manage only your own appointments" )

    if appointment.status != AppointmentStatus.BOOKED:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="Only booked appointments can be changed" )

    return appointment


def _check_cancellation_deadline(appointment: Appointment) -> None:
    appointment_datetime = datetime.combine( appointment.appointment_date, appointment.slot_time )
    if appointment_datetime - datetime.now() < timedelta(hours=2):
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="Appointments can only be changed at least two hours before the slot" )


def cancel_appointment( db: Session, patient: User, appointment_id: int ) -> Appointment:
    appointment = _get_patient_appointment(db, patient, appointment_id)
    _check_cancellation_deadline(appointment)
    # Serialize cancellation with booking and token renumbering for this doctor.
    db.query(Doctor.id).filter(Doctor.id == appointment.doctor_id).with_for_update().first()

    old_status = appointment.status
    appointment.status = AppointmentStatus.CANCELLED
    db.add( AppointmentHistory(
            appointment_id=appointment.id,
            old_status=old_status,
            new_status=AppointmentStatus.CANCELLED,
            changed_by=patient.id ) )
    _renumber_active_appointments( db,appointment.doctor_id,appointment.appointment_date )
    db.commit()
    db.refresh(appointment)
    return appointment


def reschedule_appointment( db: Session, patient: User, appointment_id: int, data: AppointmentReschedule ) -> Appointment:
    appointment = _get_patient_appointment(db, patient, appointment_id)
    _check_cancellation_deadline(appointment)
    db.query(User.id).filter(User.id == patient.id).with_for_update().first()
    old_date = appointment.appointment_date

    if appointment.reschedule_count >= 2:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, 
                            detail="This appointment has already been rescheduled twice" )

    if ( data.appointment_date == appointment.appointment_date 
         and data.slot_time == appointment.slot_time ):
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST,detail="Choose a different appointment slot" )

    today = date.today()
    if data.appointment_date <= today:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="Appointments must be rescheduled to a future date" )
    if data.appointment_date > today + timedelta(days=30):
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="Appointments can be booked at most 30 days in advance" )
    if datetime.combine(data.appointment_date, data.slot_time) <= datetime.now():
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="The selected appointment slot is in the past" )

    doctor = (
        db.query(Doctor)
        .filter( Doctor.id == appointment.doctor_id, Doctor.is_active.is_(True) )
        .with_for_update() .first() )
    if doctor is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND,detail="Active doctor not found" )

    slots = get_available_slots(db, doctor.id, data.appointment_date)
    if data.slot_time not in slots:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="The selected slot is unavailable")

    patient_conflict = ( db.query(Appointment.id) .filter(
                 Appointment.patient_id == patient.id,
                 Appointment.appointment_date == data.appointment_date,
                 Appointment.slot_time == data.slot_time,
                 Appointment.status.in_(ACTIVE_STATUSES),
                 Appointment.id != appointment.id ) .first() )
    if patient_conflict is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, 
                            detail="You already have an appointment at this date and time" )

    doctor_day_conflict = ( db.query(Appointment.id)
        .filter(Appointment.patient_id == patient.id,
                Appointment.doctor_id == doctor.id,
                Appointment.appointment_date == data.appointment_date,
                Appointment.status.in_(ACTIVE_STATUSES),
                Appointment.id != appointment.id ) .first())
    if doctor_day_conflict is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="You can book only one appointment with this doctor per day" )

    appointment.appointment_date = data.appointment_date
    appointment.slot_time = data.slot_time
    appointment.reschedule_count += 1

    try:
        db.flush()
        _renumber_active_appointments(db, doctor.id, old_date)
        _renumber_active_appointments(db, doctor.id, data.appointment_date)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="The selected slot conflicts with another appointment" )

    db.refresh(appointment)
    return appointment


def check_in_appointment( db: Session, appointment_id: int, changed_by: int ) -> Appointment:
    appointment = ( db.query(Appointment) .filter(Appointment.id == appointment_id) 
                   .with_for_update() .first() )
    if appointment is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Appointment not found" )

    if appointment.status != AppointmentStatus.BOOKED:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, 
                            detail="Only booked appointments can be checked in" )

    now = datetime.now()
    if appointment.appointment_date != now.date():
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Check-in is allowed only on the appointment date" )

    check_in_opens = datetime.combine( appointment.appointment_date, appointment.slot_time ) - timedelta(minutes=30)
    if now < check_in_opens:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Check-in opens 30 minutes before the appointment" )

    old_status = appointment.status
    appointment.status = AppointmentStatus.CHECKED_IN
    db.add( AppointmentHistory( appointment_id=appointment.id,
                                old_status=old_status,
                                new_status=AppointmentStatus.CHECKED_IN,
                                changed_by=changed_by ))
    db.commit()
    db.refresh(appointment)
    return appointment