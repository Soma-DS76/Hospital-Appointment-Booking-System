from datetime import date ,datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


from app.models.uploaded_file import FileType


class LeaveCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None, max_length=255)


class LeaveResponse(BaseModel):
    id: int
    doctor_id: int
    start_date: date
    end_date: date
    reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)



class UploadedFileResponse(BaseModel):
    id: int
    appointment_id: int
    uploaded_by: int
    file_type: FileType
    original_name: str
    size_kb: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
