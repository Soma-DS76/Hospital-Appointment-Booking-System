from datetime import date

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    report_date: date
    total_appointments: int
    checked_in: int
    completed: int
    cancelled: int
    no_shows: int
    consultation_revenue: float

    model_config = ConfigDict(from_attributes=True)


class DoctorPerformance(BaseModel):
    doctor_id: int
    doctor_name: str
    appointments: int
    completed_consultations: int
    no_show_count: int
    no_show_percentage: float
    revenue: float

    model_config = ConfigDict(from_attributes=True)


class DepartmentSummaryItem(BaseModel):
    department_id: int
    department_name: str
    appointment_count: int

    model_config = ConfigDict(from_attributes=True)


class PeakHourItem(BaseModel):
    hour: int
    appointment_count: int

    model_config = ConfigDict(from_attributes=True)


class FrequentNoShowItem(BaseModel):
    patient_id: int
    patient_name: str
    no_show_count: int

    model_config = ConfigDict(from_attributes=True)