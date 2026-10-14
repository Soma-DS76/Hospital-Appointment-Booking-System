import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User


logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP( settings.SMTP_HOST,settings.SMTP_PORT,timeout=20 ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Failed to send email to %s", to_email)
        return False


def queue_appointment_email( background_tasks: BackgroundTasks,db: Session,appointment: Appointment,event: str ) -> None:
    patient = db.query(User).filter(User.id == appointment.patient_id).first()
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()

    if patient is None or doctor is None:
        logger.error( "Cannot queue %s email for appointment %s: patient or doctor not found",
                     event, appointment.id )
        return

    event_text = { "booked": ("Appointment booked", "Your appointment has been booked."),
        "rescheduled": ("Appointment rescheduled", "Your appointment has been rescheduled."),
        "cancelled": ("Appointment cancelled", "Your appointment has been cancelled."),
        "doctor_leave": ( "Appointment cancelled", "Your appointment was cancelled because the doctor is on leave." ),
        "completed": ("Consultation completed", "Your consultation is complete.")}
    subject_and_intro: Optional[tuple] = event_text.get(event)
    if subject_and_intro is None:
        logger.error("Unknown appointment email event: %s", event)
        return

    subject, intro = subject_and_intro
    body = ( f"Hello {patient.full_name},\n\n"
             f"{intro}\n\n"
             f"Appointment number: {appointment.appointment_number}\n"
             f"Doctor: {doctor.name}\n"
             f"Date: {appointment.appointment_date:%Y-%m-%d}\n"
             f"Time: {appointment.slot_time:%H:%M}\n"
             f"Token number: {appointment.token_number}\n" )

    if event == "completed":
        from app.models.consultation import Consultation

        consultation = ( db.query(Consultation)
                        .filter(Consultation.appointment_id == appointment.id).first() )
        if consultation is not None and consultation.follow_up_date is not None:
            body += f"Follow-up date: {consultation.follow_up_date:%Y-%m-%d}\n"

    background_tasks.add_task( send_email, patient.email, subject, body )