from datetime import date
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_history import AppointmentHistory
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.consultation import ConsultationCreate
from app.services.appointment_service import get_appointment


def write_consultation( db: Session, appointment_id: int, doctor_user: User, data: ConsultationCreate ) -> Consultation:
    if doctor_user.role != "doctor":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="Only the doctor assigned to the appointment can write a consultation" )

    appointment = get_appointment(db, doctor_user, appointment_id)

    doctor = ( db.query(Doctor) .filter(Doctor.user_id == doctor_user.id) .first() )
    if doctor is None or doctor.id != appointment.doctor_id:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="Only the doctor assigned to the appointment can write a consultation" )

    if appointment.status != AppointmentStatus.IN_CONSULTATION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The appointment must be in consultation before saving a consultation",
        )

    consultation = Consultation( appointment_id=appointment.id, 
                                symptoms=data.symptoms, 
                                diagnosis=data.diagnosis, 
                                prescription=( [item.model_dump() for item in data.prescription] 
                                              if data.prescription is not None 
                                              else None ), advice=data.advice, follow_up_date=data.follow_up_date )
    old_status = appointment.status
    appointment.status = AppointmentStatus.COMPLETED
    db.add(consultation)
    db.add( AppointmentHistory( appointment_id=appointment.id,
                               old_status=old_status, 
                               new_status=AppointmentStatus.COMPLETED, 
                               changed_by=doctor_user.id ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, 
                            detail="A consultation has already been saved for this appointment" )

    db.refresh(consultation)
    return consultation


def read_consultation( db: Session, appointment_id: int, current_user: User ) -> Consultation:
    get_appointment(db, current_user, appointment_id)

    consultation = ( db.query(Consultation) .filter(Consultation.appointment_id == appointment_id) .first() )
    if consultation is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found" )
    return consultation


def get_patient_history( db: Session, patient: User, skip: int = 0, limit: int = 50 ) -> List[dict]:
    if patient.role != "patient":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is for patients only" )

    appointments = ( db.query(Appointment) 
                     .filter( Appointment.patient_id == patient.id, 
                      Appointment.appointment_date < date.today() )
                     .order_by( Appointment.appointment_date.desc(), Appointment.slot_time.desc() ) .offset(skip) .limit(limit) .all() )

    appointment_ids = [item.id for item in appointments]
    consultations = {}
    files_by_appointment = {}

    if appointment_ids:
        for item in ( db.query(Consultation)
            .filter(Consultation.appointment_id.in_(appointment_ids))
            .all() ):
            consultations[item.appointment_id] = item

        for uploaded_file in ( db.query(UploadedFile)
            .filter(UploadedFile.appointment_id.in_(appointment_ids))
            .order_by(UploadedFile.created_at)
            .all() ):
            files_by_appointment.setdefault( uploaded_file.appointment_id, []).append(uploaded_file)

    return [ { "appointment": appointment,
                "diagnosis": ( consultations[appointment.id].diagnosis 
                            if appointment.id in consultations else None ),
                "files": files_by_appointment.get(appointment.id, []) }
                for appointment in appointments ]