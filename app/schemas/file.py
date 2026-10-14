from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.uploaded_file import FileType


class UploadedFileResponse(BaseModel):
    id: int
    appointment_id: int
    uploaded_by: int
    file_type: FileType
    original_name: str
    size_kb: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)