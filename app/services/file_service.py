import logging
import os
from math import ceil
from typing import List, Tuple
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.uploaded_file import FileType, UploadedFile
from app.models.user import User
from app.services.appointment_service import get_appointment


logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_SIGNATURES = { ".pdf": b"%PDF-", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".png": b"\x89PNG\r\n\x1a\n" }


def save_appointment_file( db: Session, current_user: User, appointment_id: int, file_type: FileType, original_name: str, content: bytes ) -> UploadedFile:
    
    appointment = get_appointment(db, current_user, appointment_id)

    if current_user.role == "patient":
        if appointment.patient_id != current_user.id or file_type != FileType.LAB_REPORT:
            raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="Patients may upload lab reports only to their own appointments" )
    elif current_user.role == "doctor":
        doctor = ( db.query(Doctor) .filter(Doctor.user_id == current_user.id) .first() )
        if ( doctor is None or appointment.doctor_id != doctor.id 
            or file_type not in (FileType.PRESCRIPTION, FileType.SCAN) ):
            raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, 
                                detail="Doctors may upload prescriptions or scans only for their own patients" )
    else:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="This account cannot upload appointment files" )

    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException( status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                             detail="File exceeds the 5 MB size limit" )

    safe_original_name = os.path.basename(original_name.replace("\\", "/"))
    extension = os.path.splitext(safe_original_name)[1].lower()
    expected_signature = ALLOWED_SIGNATURES.get(extension)

    if ( expected_signature is None 
        or not content.startswith(expected_signature)
        or not safe_original_name ):
        raise HTTPException( status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
                             detail="Only valid PDF, JPG, and PNG files are allowed" )

    stored_name = f"{uuid4().hex}{extension}"
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    destination = os.path.join(upload_dir, stored_name)

    with open(destination, "xb") as uploaded:
        uploaded.write(content)

    record = UploadedFile( appointment_id=appointment.id, 
                           uploaded_by=current_user.id, 
                           file_type=file_type,
                           original_name=safe_original_name[:255], 
                           stored_name=stored_name,
                           size_kb=max(1, ceil(len(content) / 1024)))
    db.add(record)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        try:
            os.remove(destination)
        except OSError:
            logger.exception("Could not remove untracked uploaded file %s", stored_name)
        raise

    db.refresh(record)
    return record


def list_appointment_files( db: Session, current_user: User, appointment_id: int, skip: int = 0, limit: int = 50 ) -> List[UploadedFile]:
    get_appointment(db, current_user, appointment_id)
    return ( db.query(UploadedFile) .filter(UploadedFile.appointment_id == appointment_id) 
            .order_by(UploadedFile.created_at) .offset(skip) .limit(limit) .all())


def get_downloadable_file( db: Session, current_user: User,file_id: int ) -> Tuple[UploadedFile, str]:
    record = ( db.query(UploadedFile) .filter(UploadedFile.id == file_id).first())
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found" )

    get_appointment(db, current_user, record.appointment_id)
    path = os.path.join(settings.UPLOAD_DIR, record.stored_name)

    if not os.path.isfile(path):
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="The stored file is missing" )

    return record, path