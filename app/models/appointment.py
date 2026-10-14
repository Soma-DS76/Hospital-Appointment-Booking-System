from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import ( CheckConstraint, Date, Enum as SQLAlchemyEnum,
                         ForeignKey, Integer, Numeric, String, Time )
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AppointmentStatus(str, Enum):
    BOOKED = "Booked"
    CHECKED_IN = "Checked-In"
    IN_CONSULTATION = "In Consultation"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "No-Show"


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint( "token_number > 0", name="ck_appointment_token_positive" ),
        CheckConstraint( "reschedule_count >= 0 AND reschedule_count <= 2", name="ck_appointment_reschedule_count" ),
        CheckConstraint( "consultation_fee > 0", name="ck_appointment_fee_positive" ))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_number: Mapped[str] = mapped_column( String(30),unique=True,index=True,nullable=False )
    patient_id: Mapped[int] = mapped_column( ForeignKey("users.id"),index=True,nullable=False )
    doctor_id: Mapped[int] = mapped_column( ForeignKey("doctors.id"),index=True,nullable=False )
    appointment_date: Mapped[date] = mapped_column(Date, index=True, nullable=False )
    slot_time: Mapped[time] = mapped_column(Time, nullable=False)
    token_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column( SQLAlchemyEnum( AppointmentStatus, values_callable=lambda 
                                                                      enum_type: [ item.value for item in enum_type ],
                                                                      native_enum=False,length=30 ),
                                                                      default=AppointmentStatus.BOOKED,nullable=False )
    consultation_fee: Mapped[Decimal] = mapped_column( Numeric(10, 2),nullable=False )
    reschedule_count: Mapped[int] = mapped_column( Integer,default=0,nullable=False )
    reminder_sent: Mapped[bool] = mapped_column( default=False, nullable=False )
    follow_up_reminder_sent: Mapped[bool] = mapped_column( default=False, nullable=False )

    patient = relationship("User", back_populates="appointments", foreign_keys=[patient_id])
    doctor = relationship("Doctor", back_populates="appointments")
    history = relationship("AppointmentHistory", back_populates="appointment", cascade="all, delete-orphan")
    consultation = relationship("Consultation", back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    files = relationship("UploadedFile", back_populates="appointment", cascade="all, delete-orphan")