from typing import List

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models.department import Department
from app.schemas.department import ( DepartmentCreate, DepartmentResponse, DepartmentUpdate )
from app.services.department_service import (create_department, delete_department,list_departments,update_department )

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post( "", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED,dependencies=[Depends(require_roles("admin"))])
def create( payload: DepartmentCreate, db: Session = Depends(get_db)) -> Department:
    return create_department(db, payload)


@router.get("", response_model=List[DepartmentResponse])
def list_all( skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), 
             db: Session = Depends(get_db)) -> List[Department]:
    return list_departments(db, skip=skip, limit=limit)


@router.put( "/{department_id}", response_model=DepartmentResponse, dependencies=[Depends(require_roles("admin"))] )
def update( department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db)) -> Department:
    return update_department(db, department_id, payload)


@router.delete( "/{department_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("admin"))])
def delete( department_id: int, db: Session = Depends(get_db)) -> Response:
    delete_department(db, department_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)