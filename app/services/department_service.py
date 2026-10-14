from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.doctor import Doctor
from app.schemas.department import DepartmentCreate, DepartmentUpdate


def create_department(db: Session, data: DepartmentCreate) -> Department:
    name = data.name.strip()
    if not name:
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Department name cannot be blank" )

    department = Department( name=name, description=data.description )
    db.add(department)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="A department with this name already exists" )

    db.refresh(department)
    return department


def list_departments(db: Session, skip: int = 0, limit: int = 50) -> list[Department]:
    return ( db.query(Department) .order_by(Department.name) .offset(skip) .limit(limit) .all() )


def update_department( db: Session, department_id: int, data: DepartmentUpdate ) -> Department:
    department = ( db.query(Department) .filter(Department.id == department_id) .first() )
    if department is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Department not found" )

    name = data.name.strip()
    if not name:
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Department name cannot be blank" )

    department.name = name
    department.description = data.description

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="A department with this name already exists" )

    db.refresh(department)
    return department


def delete_department(db: Session, department_id: int) -> None:
    department = ( db.query(Department) .filter(Department.id == department_id) .first() )
    if department is None:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Department not found" )

    has_active_doctors = ( db.query(Doctor.id) .filter( Doctor.department_id == department_id, Doctor.is_active.is_(True) ) .first() is not None )
    if has_active_doctors:
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="Cannot delete a department with active doctors" )

    db.delete(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="Cannot delete this department while doctor profiles reference it" )