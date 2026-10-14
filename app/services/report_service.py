from datetime import date, timedelta
from decimal import Decimal
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import Integer, case, extract, func
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.report import (
    DashboardSummary,
    DepartmentSummaryItem,
    DoctorPerformance,
    FrequentNoShowItem,
    PeakHourItem,
)


def get_dashboard_summary(db: Session, report_date: date) -> DashboardSummary:
    row = ( db.query( func.count(Appointment.id).label("total_appointments"),
                      func.sum(case((Appointment.status == AppointmentStatus.CHECKED_IN, 1), else_=0)).label("checked_in"),
                      func.sum(case((Appointment.status == AppointmentStatus.COMPLETED, 1), else_=0)).label("completed"),
                      func.sum(case((Appointment.status == AppointmentStatus.CANCELLED, 1), else_=0)).label("cancelled"),
                      func.sum(case((Appointment.status == AppointmentStatus.NO_SHOW, 1), else_=0)).label("no_shows"),
                      func.sum(case((Appointment.status == AppointmentStatus.COMPLETED, Appointment.consultation_fee), else_=0)).label("consultation_revenue"))
        .filter(Appointment.appointment_date == report_date)
        .first() )

    if row is None:
        return DashboardSummary( report_date=report_date,total_appointments=0,
                                 checked_in=0,completed=0,cancelled=0,no_shows=0,consultation_revenue=0.0)

    return DashboardSummary( report_date=report_date,
                             total_appointments=int(row.total_appointments or 0),
                             checked_in=int(row.checked_in or 0),
                             completed=int(row.completed or 0),
                             cancelled=int(row.cancelled or 0),
                             no_shows=int(row.no_shows or 0),
                             consultation_revenue=float(row.consultation_revenue or Decimal("0.00")))


def get_doctor_performance(db: Session, start_date: date, end_date: date) -> List[DoctorPerformance]:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date must be on or after start_date")

    rows = (db.query(
            Doctor.id.label("doctor_id"),
            Doctor.name.label("doctor_name"),
            func.count(Appointment.id).label("appointments"),
            func.sum(case((Appointment.status == AppointmentStatus.COMPLETED, 1), else_=0)).label("completed_consultations"),
            func.sum(case((Appointment.status == AppointmentStatus.NO_SHOW, 1), else_=0)).label("no_show_count"),
            func.sum(case((Appointment.status == AppointmentStatus.COMPLETED, Appointment.consultation_fee), else_=0)).label("revenue"))
        .outerjoin(Appointment, (Appointment.doctor_id == Doctor.id) & (Appointment.appointment_date >= start_date) & (Appointment.appointment_date <= end_date))
        .filter(Doctor.is_active.is_(True))
        .group_by(Doctor.id, Doctor.name)
        .order_by(Doctor.name)
        .all())

    results: List[DoctorPerformance] = []
    for row in rows:
        appointments = int(row.appointments or 0)
        completed_consultations = int(row.completed_consultations or 0)
        no_show_count = int(row.no_show_count or 0)
        no_show_percentage = (no_show_count / appointments * 100) if appointments else 0.0

        results.append(
            DoctorPerformance(
                doctor_id=row.doctor_id,
                doctor_name=row.doctor_name,
                appointments=appointments,
                completed_consultations=completed_consultations,
                no_show_count=no_show_count,
                no_show_percentage=no_show_percentage,
                revenue=float(row.revenue or Decimal("0.00"))))

    return results


def get_department_summary(db: Session, start_date: date, end_date: date) -> List[DepartmentSummaryItem]:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date must be on or after start_date")

    rows = (
        db.query(
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            func.count(Appointment.id).label("appointment_count"))
        .join(Doctor, Doctor.department_id == Department.id)
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .filter(
            Doctor.is_active.is_(True),
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date)
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
        .all())

    return [DepartmentSummaryItem(
            department_id=row.department_id,
            department_name=row.department_name,
            appointment_count=int(row.appointment_count or 0))
        for row in rows ]


def get_peak_hours(db: Session, start_date: date, end_date: date) -> List[PeakHourItem]:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date must be on or after start_date")

    hour_expr = func.cast(extract('hour', Appointment.slot_time), Integer)

    rows = ( db.query( hour_expr.label("hour"),func.count(Appointment.id).label("appointment_count"))
        .filter( Appointment.appointment_date >= start_date,Appointment.appointment_date <= end_date )
        .group_by(hour_expr) .order_by(hour_expr) .all())

    return [ PeakHourItem(hour=int(row.hour or 0), appointment_count=int(row.appointment_count or 0))
        for row in rows ]


def get_frequent_no_shows(db: Session, days: int = 90) -> List[FrequentNoShowItem]:
    if days <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="days must be greater than zero")

    cutoff_date = date.today() - timedelta(days=days)

    rows = ( db.query(
            User.id.label("patient_id"),
            User.full_name.label("patient_name"),
            func.count(Appointment.id).label("no_show_count") )
        .join(Appointment, Appointment.patient_id == User.id)
        .filter( Appointment.status == AppointmentStatus.NO_SHOW,Appointment.appointment_date >= cutoff_date)
        .group_by(User.id, User.full_name)
        .having(func.count(Appointment.id) >= 3)
        .order_by(func.count(Appointment.id).desc(), User.full_name.asc())
        .all())

    return [ FrequentNoShowItem(
            patient_id=row.patient_id,
            patient_name=row.patient_name,
            no_show_count=int(row.no_show_count or 0) )
        for row in rows ]