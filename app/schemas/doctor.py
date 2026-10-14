from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DoctorCreate(BaseModel):
    user_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=150)
    department_id: int = Field(gt=0)
    specialization: str = Field(min_length=2, max_length=150)
    qualification: str = Field(min_length=2, max_length=200)
    experience_years: int = Field(default=0, ge=0)
    consultation_fee: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    slot_duration_minutes: Literal[10, 15, 20, 30] = 15


class DoctorUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    department_id: int = Field(gt=0)
    specialization: str = Field(min_length=2, max_length=150)
    qualification: str = Field(min_length=2, max_length=200)
    experience_years: int = Field(ge=0)
    consultation_fee: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    slot_duration_minutes: Literal[10, 15, 20, 30]
    is_active: bool = True


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    name: str
    department_id: int
    specialization: str
    qualification: str
    experience_years: int
    consultation_fee: Decimal
    slot_duration_minutes: int
    is_active: bool 

    model_config = ConfigDict(from_attributes=True)