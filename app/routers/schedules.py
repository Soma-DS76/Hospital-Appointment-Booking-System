from datetime import date
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.leave import DoctorLeave
from app.models.schedule import DoctorSchedule
from app.models.user import User
from app.schemas.leave import LeaveCreate, LeaveResponse
from app.schemas.schedule import ( AvailableSlotsResponse, ScheduleCreate, ScheduleResponse )
from app.services.schedule_service import ( create_leave, create_schedule, delete_schedule, get_available_slots, 
                                            list_leaves, list_schedules, update_schedule)

router = APIRouter(tags=["Doctor schedules and leave"])


@router.post( "/doctors/{doctor_id}/schedules", response_model=ScheduleResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles("admin", "doctor"))])
def add_schedule( doctor_id: int, payload: ScheduleCreate,
                 current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DoctorSchedule:
    return create_schedule( db, doctor_id, payload, current_user.id, current_user.role )


@router.get( "/doctors/{doctor_id}/schedules", response_model=List[ScheduleResponse] )
def read_schedules( doctor_id: int, skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db) ) -> List[DoctorSchedule]:
    return list_schedules(db, doctor_id, skip=skip, limit=limit)


@router.put( "/schedules/{schedule_id}", response_model=ScheduleResponse, dependencies=[Depends(require_roles("admin", "doctor"))])
def edit_schedule( schedule_id: int, payload: ScheduleCreate, 
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db),) -> DoctorSchedule:
    return update_schedule( db, schedule_id, payload, current_user.id, current_user.role   )


@router.delete( "/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, 
               dependencies=[Depends(require_roles("admin", "doctor"))])
def remove_schedule( schedule_id: int, current_user: User = Depends(get_current_user),db: Session = Depends(get_db)) -> Response:
    delete_schedule( db, schedule_id, current_user.id, current_user.role )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post( "/doctors/{doctor_id}/leaves", response_model=LeaveResponse,status_code=status.HTTP_201_CREATED,dependencies=[Depends(require_roles("admin", "doctor"))])
def add_leave( doctor_id: int,payload: LeaveCreate,background_tasks: BackgroundTasks,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> DoctorLeave:
    return create_leave( db,doctor_id,payload,current_user.id,current_user.role,background_tasks)


@router.get( "/doctors/{doctor_id}/leaves", response_model=List[LeaveResponse])
def read_leaves( doctor_id: int, skip: int = Query(default=0, ge=0),limit: int = Query(default=50, ge=1, le=100),
                db: Session = Depends(get_db)) -> List[DoctorLeave]:
    return list_leaves(db, doctor_id, skip=skip, limit=limit)


@router.get( "/doctors/{doctor_id}/available-slots", response_model=AvailableSlotsResponse )
def read_available_slots( doctor_id: int, date: date = Query(...), db: Session = Depends(get_db)) -> AvailableSlotsResponse:
    return AvailableSlotsResponse( doctor_id=doctor_id, date=date, slots=get_available_slots(db, doctor_id, date))