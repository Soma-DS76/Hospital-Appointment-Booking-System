from datetime import date, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    appointment_date: date
    slot_time: time
    reason: Optional[str] = Field(default=None, max_length=500)


class AppointmentResponse(BaseModel):
    id: int
    appointment_number: str
    patient_id: int
    doctor_id: int
    appointment_date: date
    slot_time: time
    token_number: int
    reason: Optional[str]
    status: AppointmentStatus
    consultation_fee: Decimal
    reschedule_count: int

    model_config = ConfigDict(from_attributes=True)

class AppointmentReschedule(BaseModel):
    appointment_date: date
    slot_time: time