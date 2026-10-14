from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.appointment import AppointmentResponse
from app.schemas.file import UploadedFileResponse


class PrescriptionItem(BaseModel):
    medicine: str = Field(min_length=1, max_length=150)
    dosage: str = Field(min_length=1, max_length=100)
    days: int = Field(gt=0)


class ConsultationCreate(BaseModel):
    symptoms: str = Field(min_length=1)
    diagnosis: str = Field(min_length=1)
    prescription: Optional[List[PrescriptionItem]] = None
    advice: Optional[str] = None
    follow_up_date: Optional[date] = None


class ConsultationResponse(BaseModel):
    id: int
    appointment_id: int
    symptoms: str
    diagnosis: str
    prescription: Optional[List[PrescriptionItem]]
    advice: Optional[str]
    follow_up_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class PatientHistoryItem(BaseModel):
    appointment: AppointmentResponse
    diagnosis: Optional[str]
    files: List[UploadedFileResponse]