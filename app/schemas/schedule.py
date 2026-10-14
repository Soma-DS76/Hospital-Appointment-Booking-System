from datetime import date, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="Monday=0, Sunday=6")
    start_time: time
    end_time: time
    break_start: Optional[time] = None
    break_end: Optional[time] = None


class ScheduleResponse(BaseModel):
    id: int
    doctor_id: int
    day_of_week: int
    start_time: time
    end_time: time
    break_start: Optional[time]
    break_end: Optional[time]

    model_config = ConfigDict(from_attributes=True)


class AvailableSlotsResponse(BaseModel):
    doctor_id: int
    date: date
    slots: List[time]