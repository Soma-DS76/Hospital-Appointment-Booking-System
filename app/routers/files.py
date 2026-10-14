from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.uploaded_file import FileType, UploadedFile
from app.models.user import User
from app.schemas.file import UploadedFileResponse
from app.services.file_service import ( get_downloadable_file, list_appointment_files, save_appointment_file)

router = APIRouter(tags=["Appointment files"])


@router.post( "/appointments/{appointment_id}/files", response_model=UploadedFileResponse, 
             status_code=status.HTTP_201_CREATED )
async def upload_file(  appointment_id: int,
                        file_type: FileType = Form(...),
                        file: UploadFile = File(...),
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> UploadedFile:
    try:
        content = await file.read(5 * 1024 * 1024 + 1)
        return save_appointment_file(db, current_user,appointment_id, 
                                     file_type,file.filename or "",content)
    finally:
        await file.close()


@router.get( "/appointments/{appointment_id}/files", response_model=List[UploadedFileResponse])
def get_files( appointment_id: int, skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[UploadedFile]:
    return list_appointment_files(db, current_user, appointment_id, skip=skip, limit=limit)


@router.get("/files/{file_id}/download")
def download_file( file_id: int,current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> FileResponse:
    record, path = get_downloadable_file(db, current_user, file_id)
    return FileResponse( path, filename=record.original_name, media_type="application/octet-stream" )