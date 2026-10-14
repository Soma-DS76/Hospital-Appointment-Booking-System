from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.report import ( DashboardSummary,DepartmentSummaryItem,
                                 DoctorPerformance,FrequentNoShowItem,PeakHourItem)
from app.services.report_service import ( get_dashboard_summary,get_department_summary,
                                          get_doctor_performance,get_frequent_no_shows,
                                          get_peak_hours )

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard( current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,
                             detail="Only admins can access this dashboard")
    return get_dashboard_summary(db, date.today())


@router.get("/doctor-performance", response_model=List[DoctorPerformance])
def doctor_performance(start_date: date = Query(...),end_date: date = Query(...),current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins can access doctor performance reports")
    return get_doctor_performance(db, start_date, end_date)


@router.get("/department-summary", response_model=List[DepartmentSummaryItem])
def department_summary( start_date: date = Query(...),end_date: date = Query(...),
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,
                             detail="Only admins can access department summaries")
    return get_department_summary(db, start_date, end_date)


@router.get("/peak-hours", response_model=List[PeakHourItem])
def peak_hours( start_date: date = Query(...),end_date: date = Query(...),
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,detail="Only admins can access peak-hour reports")
    return get_peak_hours(db, start_date, end_date)


@router.get("/frequent-no-shows", response_model=List[FrequentNoShowItem])
def frequent_no_shows(days: int = Query(default=90, ge=1),current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only admins can access frequent no-show reports")
    return get_frequent_no_shows(db, days=days)