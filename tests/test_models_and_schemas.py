from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers

from app.models import Department, Doctor, DoctorSchedule, User
from app.schemas.auth import AdminUserCreate, RegisterRequest
from app.schemas.doctor import DoctorCreate
from app.schemas.schedule import ScheduleCreate


def test_patient_registration_schema_rejects_invalid_phone():
    with pytest.raises(ValidationError):
        RegisterRequest(full_name="Test Patient",
                        email="patient@example.com",
                        phone="12345",
                        password="password123")


def test_public_registration_does_not_accept_role():
    payload = RegisterRequest(  full_name="Test Patient",
                                email="patient@example.com",
                                phone="9876543210",
                                password="password123" )
    assert not hasattr(payload, "role")


def test_admin_staff_schema_only_allows_staff_roles():
    with pytest.raises(ValidationError):
        AdminUserCreate(
            full_name="Test Patient",
            email="patient@example.com",
            phone="9876543210",
            password="password123",
            role="patient" )


def test_doctor_schema_rejects_invalid_slot_duration():
    with pytest.raises(ValidationError):
        DoctorCreate( user_id=1,
                      name="Doctor One",
                      department_id=1,
                      specialization="General Medicine",
                      qualification="MBBS",
                      experience_years=2,
                      consultation_fee=Decimal("250.00"),
                      slot_duration_minutes=12)


def test_schedule_schema_rejects_invalid_weekday():
    with pytest.raises(ValidationError):
        ScheduleCreate( day_of_week=7,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                        break_start=time(13, 0),
                        break_end=time(14, 0))


def test_all_model_relationships_configure():
    configure_mappers()
    assert hasattr(User, "appointments")
    assert hasattr(Department, "doctors")
    assert hasattr(Doctor, "schedules")
    assert hasattr(Doctor, "leaves")


def test_timestamp_fields_are_present_on_core_models():
    for model in (User, Department, Doctor, DoctorSchedule):
        assert "created_at" in model.__table__.columns
        assert "updated_at" in model.__table__.columns
