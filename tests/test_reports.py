from datetime import date, time
from decimal import Decimal

from app.models import Appointment, AppointmentStatus, Department, Doctor, User
from app.services.report_service import get_dashboard_summary, get_doctor_performance


def _seed_appointments(db_session):
    patient = User( full_name="Patient One", email="patient@example.com", phone="9876543210",
                    hashed_password="hashed", role="patient", is_active=True )
    staff = User( full_name="Doctor One", email="doctor@example.com", phone="9876543211",
                  hashed_password="hashed", role="doctor", is_active=True )
    department = Department(name="General Medicine", description=None)
    db_session.add_all([patient, staff, department])
    db_session.flush()
    doctor = Doctor( user_id=staff.id, name="Doctor One", department_id=department.id,
                     specialization="General Medicine", qualification="MBBS", experience_years=5,
                     consultation_fee=Decimal("250.00"), slot_duration_minutes=15, is_active=True )
    db_session.add(doctor)
    db_session.flush()
    target = date(2026, 10, 20)
    db_session.add_all([Appointment(  appointment_number="APT-TEST-0001", patient_id=patient.id, doctor_id=doctor.id,
                                      appointment_date=target, slot_time=time(10, 0), token_number=1,
                                      status=AppointmentStatus.COMPLETED, consultation_fee=Decimal("250.00")),
                        Appointment(appointment_number="APT-TEST-0002", patient_id=patient.id, doctor_id=doctor.id,
                                    appointment_date=target, slot_time=time(10, 15), token_number=2,
                                    status=AppointmentStatus.CANCELLED, consultation_fee=Decimal("250.00"))])
    db_session.commit()
    return target


def test_dashboard_revenue_counts_completed_consultations_only(db_session):
    target = _seed_appointments(db_session)
    report = get_dashboard_summary(db_session, target)
    assert report.total_appointments == 2
    assert report.completed == 1
    assert report.cancelled == 1
    assert report.consultation_revenue == 250.0


def test_doctor_performance_revenue_counts_completed_only(db_session):
    target = _seed_appointments(db_session)
    report = get_doctor_performance(db_session, target, target)
    assert len(report) == 1
    assert report[0].appointments == 2
    assert report[0].completed_consultations == 1
    assert report[0].revenue == 250.0
