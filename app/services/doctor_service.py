from datetime import date, datetime, time
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorUpdate


def create_doctor(db: Session, data: DoctorCreate) -> Doctor:
    user = db.query(User).filter(User.id == data.user_id).first()
    if user is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Doctor user account not found" )
    if user.role != "doctor":
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, 
                             detail="The selected user account must have the doctor role" )

    department = ( db.query(Department) .filter(Department.id == data.department_id) 
                  .first())
    if department is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Department not found" )

    doctor = Doctor(**data.model_dump())
    db.add(doctor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="This user already has a doctor profile" )

    db.refresh(doctor)
    return doctor


def list_doctors( db: Session, skip: int = 0, limit: int = 50, 
                  department_id: Optional[int] = None, 
                  specialization: Optional[str] = None,
                  name: Optional[str] = None,active_only: bool = True 
                  )-> List[Doctor]:
    query = db.query(Doctor)

    if active_only:
        query = query.filter(Doctor.is_active.is_(True))
    if department_id is not None:
        query = query.filter(Doctor.department_id == department_id)
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    if name:
        query = query.filter(Doctor.name.ilike(f"%{name}%"))

    return ( query.order_by(Doctor.name) .offset(skip) .limit(limit) .all())


def get_doctor( db: Session, doctor_id: int, active_only: bool = True ) -> Doctor:
    query = db.query(Doctor).filter(Doctor.id == doctor_id)
    if active_only:
        query = query.filter(Doctor.is_active.is_(True))

    doctor = query.first()
    if doctor is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found" )
    return doctor


def _ensure_no_upcoming_appointments(db: Session, doctor_id: int) -> None:
    now = datetime.now()
    upcoming_appointment = (
        db.query(Appointment.id)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_([
                AppointmentStatus.BOOKED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
            ]),
            (Appointment.appointment_date > now.date())
            | ((Appointment.appointment_date == now.date()) & (Appointment.slot_time > now.time())),
        )
        .first()
    )

    if upcoming_appointment is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="Doctor has upcoming appointments and cannot be deactivated" )


def update_doctor( db: Session, doctor_id: int, data: DoctorUpdate ) -> Doctor:
    doctor = get_doctor(db, doctor_id, active_only=False)

    department = ( db.query(Department) .filter(Department.id == data.department_id) .first() )
    if department is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Department not found" )

    if doctor.is_active and not data.is_active:
        _ensure_no_upcoming_appointments(db, doctor_id)

    for field, value in data.model_dump().items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)
    return doctor


def deactivate_doctor(db: Session, doctor_id: int) -> None:
    doctor = get_doctor(db, doctor_id, active_only=False)

    if doctor.is_active:
        _ensure_no_upcoming_appointments(db, doctor_id)
        doctor.is_active = False
        db.commit()