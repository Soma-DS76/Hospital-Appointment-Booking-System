import logging
from datetime import date, datetime, timedelta

from app.database import SessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_history import AppointmentHistory
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.user import User
from app.services.email_service import send_email
from app.websockets.manager import manager
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)


def send_appointment_reminders() -> None:
    now = datetime.now()
    window_end = now + timedelta(hours=24)
    today = now.date()
    last_date = window_end.date()

    db = SessionLocal()
    try:
        appointments = (
            db.query(Appointment)
            .filter( Appointment.status == AppointmentStatus.BOOKED,
                     Appointment.reminder_sent.is_(False),
                     Appointment.appointment_date >= today,
                     Appointment.appointment_date <= last_date ).all())

        for appointment in appointments:
            appointment_datetime = datetime.combine( appointment.appointment_date, appointment.slot_time )
            if not now < appointment_datetime <= window_end:
                continue

            patient = db.query(User).filter(User.id == appointment.patient_id).first()
            doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
            if patient is None or doctor is None:
                logger.error( "Cannot send reminder for appointment %s: patient or doctor not found",
                              appointment.id )
                continue

            body = ( f"Hello {patient.full_name},\n\n" "This is a reminder for your upcoming appointment.\n\n"
                     f"Appointment number: {appointment.appointment_number}\n"
                     f"Doctor: {doctor.name}\n"
                     f"Date: {appointment.appointment_date:%Y-%m-%d}\n"
                     f"Time: {appointment.slot_time:%H:%M}\n"
                     f"Token number: {appointment.token_number}\n" )

            if send_email(patient.email, "Appointment reminder", body):
                appointment.reminder_sent = True

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Appointment reminder job failed")
        raise
    finally:
        db.close()


def mark_no_show_appointments() -> None:
    now = datetime.now()
    db = SessionLocal()
    affected_doctors = set()
    try:
        overdue = (
            db.query(Appointment)
            .filter( Appointment.status == AppointmentStatus.BOOKED,
                     Appointment.appointment_date <= now.date()) .with_for_update().all() )

        for appointment in overdue:
            slot_datetime = datetime.combine( appointment.appointment_date,appointment.slot_time )
            if now < slot_datetime + timedelta(minutes=30):
                continue

            appointment.status = AppointmentStatus.NO_SHOW
            affected_doctors.add(appointment.doctor_id)
            db.add( AppointmentHistory(
                    appointment_id=appointment.id,
                    old_status=AppointmentStatus.BOOKED,
                    new_status=AppointmentStatus.NO_SHOW,
                    changed_by=None ))

        db.commit()
        for doctor_id in affected_doctors:
            manager.broadcast_queue_update_threadsafe(doctor_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("No-show job failed")
        raise
    finally:
        db.close()


def send_follow_up_reminders() -> None:
    tomorrow = date.today() + timedelta(days=1)
    db = SessionLocal()
    try:
        rows = ( db.query(Consultation, Appointment, User)
            .join( Appointment, Appointment.id == Consultation.appointment_id )
            .join(User, User.id == Appointment.patient_id)
            .filter(Consultation.follow_up_date == tomorrow, Appointment.follow_up_reminder_sent.is_(False))
            .all() )

        for consultation, appointment, patient in rows:
            body = ( f"Hello {patient.full_name},\n\n"
                     f"This is a reminder that your follow-up date is "
                     f"{consultation.follow_up_date:%Y-%m-%d}.\n"
                     f"Appointment number: {appointment.appointment_number}\n")
            if send_email(patient.email, "Follow-up reminder", body):
                appointment.follow_up_reminder_sent = True
        db.commit()
    except SQLAlchemyError:
        logger.exception("Follow-up reminder job failed")
        raise
    finally:
        db.close()