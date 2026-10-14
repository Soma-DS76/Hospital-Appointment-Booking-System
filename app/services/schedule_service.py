from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_history import AppointmentHistory
from app.models.doctor import Doctor
from app.models.leave import DoctorLeave
from app.models.schedule import DoctorSchedule
from app.schemas.leave import LeaveCreate
from app.schemas.schedule import ScheduleCreate
from app.services.email_service import queue_appointment_email
from app.websockets.manager import manager


def _get_doctor(db: Session, doctor_id: int) -> Doctor:
    doctor = ( db.query(Doctor).filter(Doctor.id == doctor_id, Doctor.is_active.is_(True)).first())
    if doctor is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Active doctor not found" )
    return doctor


def _check_manage_access( db: Session, doctor_id: int, actor_user_id: int, actor_role: str ) -> Doctor:
    doctor = _get_doctor(db, doctor_id)
    if actor_role != "admin" and ( actor_role != "doctor" or doctor.user_id != actor_user_id ):
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can manage only your own schedule and leave" )
    return doctor


def _lock_doctor(db: Session, doctor_id: int) -> Doctor:
    doctor = (
        db.query(Doctor)
        .filter(Doctor.id == doctor_id, Doctor.is_active.is_(True))
        .with_for_update()
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active doctor not found",
        )
    return doctor


def _validate_schedule(data: ScheduleCreate) -> None:
    if data.end_time <= data.start_time:
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                            detail="Schedule end time must be after start time")

    if (data.break_start is None) != (data.break_end is None):
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide both break_start and break_end, or neither" )

    if data.break_start is not None and data.break_end is not None:
        if not ( data.start_time <= data.break_start < data.break_end <= data.end_time ):
            raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                 detail="The break must be inside working hours" )


def _check_schedule_overlap( db: Session, doctor_id: int, data: ScheduleCreate, exclude_schedule_id: Optional[int] = None ) -> None:
    query = db.query(DoctorSchedule).filter( DoctorSchedule.doctor_id == doctor_id,
                                             DoctorSchedule.day_of_week == data.day_of_week,
                                             DoctorSchedule.start_time < data.end_time,
                                             DoctorSchedule.end_time > data.start_time)
    if exclude_schedule_id is not None:
        query = query.filter(DoctorSchedule.id != exclude_schedule_id)

    if query.first() is not None:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="This schedule overlaps another schedule on the same day" )


def create_schedule( db: Session,doctor_id: int, data: ScheduleCreate,actor_user_id: int, actor_role: str ) -> DoctorSchedule:
    _check_manage_access(db, doctor_id, actor_user_id, actor_role)
    _lock_doctor(db, doctor_id)
    _validate_schedule(data)
    _check_schedule_overlap(db, doctor_id, data)

    schedule = DoctorSchedule(doctor_id=doctor_id, **data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedules(db: Session, doctor_id: int, skip: int = 0, limit: int = 50) -> List[DoctorSchedule]:
    _get_doctor(db, doctor_id)
    return ( db.query(DoctorSchedule) .filter(DoctorSchedule.doctor_id == doctor_id) .order_by(DoctorSchedule.day_of_week, DoctorSchedule.start_time) .offset(skip) .limit(limit) .all())


def update_schedule( db: Session, schedule_id: int, data: ScheduleCreate, actor_user_id: int, actor_role: str ) -> DoctorSchedule:
    schedule = ( db.query(DoctorSchedule) .filter(DoctorSchedule.id == schedule_id) .first())
    if schedule is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found" )

    _check_manage_access(db, schedule.doctor_id, actor_user_id, actor_role)
    _lock_doctor(db, schedule.doctor_id)
    _validate_schedule(data)
    _check_schedule_overlap( db, schedule.doctor_id, data, exclude_schedule_id=schedule_id)

    for field, value in data.model_dump().items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule( db: Session, schedule_id: int, actor_user_id: int, actor_role: str ) -> None:
    schedule = ( db.query(DoctorSchedule) .filter(DoctorSchedule.id == schedule_id) .first() )
    if schedule is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND,detail="Schedule not found")

    _check_manage_access(db, schedule.doctor_id, actor_user_id, actor_role)
    _lock_doctor(db, schedule.doctor_id)
    db.delete(schedule)
    db.commit()


def create_leave(
    db: Session,
    doctor_id: int,
    data: LeaveCreate,
    actor_user_id: int,
    actor_role: str,
    background_tasks: BackgroundTasks,
) -> DoctorLeave:
    _check_manage_access(db, doctor_id, actor_user_id, actor_role)
    _lock_doctor(db, doctor_id)

    if data.end_date < data.start_date:
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                            detail="Leave end date must be on or after its start date")

    leave = DoctorLeave(doctor_id=doctor_id, **data.model_dump())
    db.add(leave)
    db.flush()

    affected_appointments = (
        db.query(Appointment).filter(
                 Appointment.doctor_id == doctor_id,
                 Appointment.appointment_date >= data.start_date,
                 Appointment.appointment_date <= data.end_date,
                 Appointment.status.in_(
                [AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN])) .with_for_update().all())

    for appointment in affected_appointments:
        old_status = appointment.status
        appointment.status = AppointmentStatus.CANCELLED
        db.add( AppointmentHistory( appointment_id=appointment.id, old_status=old_status,new_status=AppointmentStatus.CANCELLED,changed_by=actor_user_id ))

    for affected_date in {item.appointment_date for item in affected_appointments}:
        remaining_appointments = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == affected_date,
                Appointment.status.in_(
                    [
                        AppointmentStatus.BOOKED,
                        AppointmentStatus.CHECKED_IN,
                        AppointmentStatus.IN_CONSULTATION,
                    ]
                ),
            )
            .order_by(Appointment.slot_time, Appointment.id)
            .with_for_update()
            .all()
        )
        for token_number, appointment in enumerate(remaining_appointments, start=1):
            appointment.token_number = token_number

    db.commit()
    db.refresh(leave)
    for appointment in affected_appointments:
        queue_appointment_email(
            background_tasks,
            db,
            appointment,
            "doctor_leave",
        )
        background_tasks.add_task(
            manager.send_user_event,
            appointment.patient_id,
            {
                "event": "appointment_cancelled",
                "appointment_id": appointment.id,
                "reason": "doctor_leave",
            },
        )
    if affected_appointments:
        background_tasks.add_task(manager.broadcast_queue_update, doctor_id)
    return leave


def list_leaves(db: Session,doctor_id: int,skip: int = 0,limit: int = 50 ) -> List[DoctorLeave]:
    _get_doctor(db, doctor_id)
    return ( db.query(DoctorLeave) .filter(DoctorLeave.doctor_id == doctor_id)
            .order_by(DoctorLeave.start_date.desc()).offset(skip).limit(limit).all())


def get_available_slots( db: Session, doctor_id: int, target_date: date) -> List[time]:
    doctor = _get_doctor(db, doctor_id)

    if target_date < date.today():
        return []

    on_leave = ( db.query(DoctorLeave.id)
                .filter( DoctorLeave.doctor_id == doctor_id, DoctorLeave.start_date <= target_date,
                DoctorLeave.end_date >= target_date ) .first())
    if on_leave is not None:
        return []

    weekday_schedule = ( db.query(DoctorSchedule).filter(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.day_of_week == target_date.weekday())
            .order_by(DoctorSchedule.start_time).all())

    booked_slots = { appointment.slot_time
        for appointment in ( db.query(Appointment) .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == target_date,
                Appointment.status.in_( [ AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION ])).all())}

    now = datetime.now()
    available: List[time] = []
    duration = timedelta(minutes=doctor.slot_duration_minutes)

    for schedule in weekday_schedule:
        current = datetime.combine(target_date, schedule.start_time)
        end = datetime.combine(target_date, schedule.end_time)
        break_start = ( datetime.combine(target_date, schedule.break_start) if schedule.break_start is not None else None )
        break_end = ( datetime.combine(target_date, schedule.break_end) if schedule.break_end is not None else None )

        while current + duration <= end:
            slot_end = current + duration
            overlaps_break = ( break_start is not None and 
                              break_end is not None and current < break_end 
                              and slot_end > break_start )
            slot_time = current.time()

            if (
                not overlaps_break
                and slot_time not in booked_slots
                and (target_date > now.date() or current > now)
            ):
                available.append(slot_time)

            current += duration

    return sorted(set(available))