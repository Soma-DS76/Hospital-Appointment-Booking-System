from decimal import Decimal

from sqlalchemy import ( Boolean, CheckConstraint, ForeignKey, Integer, Numeric,String )
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Doctor(TimestampMixin, Base):
    __tablename__ = "doctors"
    __table_args__ = ( CheckConstraint( "consultation_fee > 0", name="ck_doctors_consultation_fee_positive" ),
                       CheckConstraint( "slot_duration_minutes IN (10, 15, 20, 30)", name="ck_doctors_slot_duration_valid" ),
                       CheckConstraint( "experience_years >= 0", name="ck_doctors_experience_nonnegative" ) )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column( ForeignKey("users.id"), unique=True,nullable=False )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    department_id: Mapped[int] = mapped_column( ForeignKey("departments.id"), index=True, nullable=False, )
    specialization: Mapped[str] = mapped_column(String(150), nullable=False)
    qualification: Mapped[str] = mapped_column(String(200), nullable=False)
    experience_years: Mapped[int] = mapped_column( Integer, default=0, nullable=False )
    consultation_fee: Mapped[Decimal] = mapped_column( Numeric(10, 2), nullable=False )
    slot_duration_minutes: Mapped[int] = mapped_column( Integer, default=15, nullable=False )
    is_active: Mapped[bool] = mapped_column( Boolean, default=True, nullable=False )

    user = relationship("User", back_populates="doctor_profile")
    department = relationship("Department", back_populates="doctors")
    schedules = relationship("DoctorSchedule", back_populates="doctor", cascade="all, delete-orphan")
    leaves = relationship("DoctorLeave", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")