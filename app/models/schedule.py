from datetime import time
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DoctorSchedule(TimestampMixin, Base):
    __tablename__ = "doctor_schedules"
    __table_args__ = (
        CheckConstraint( "day_of_week >= 0 AND day_of_week <= 6", name="ck_doctor_schedules_day_of_week"),
        CheckConstraint( "end_time > start_time",name="ck_doctor_schedules_end_after_start" ),
        CheckConstraint( "(break_start IS NULL AND break_end IS NULL) OR "
                         "(break_start IS NOT NULL AND break_end IS NOT NULL "
                          "AND break_start >= start_time "
                          "AND break_end <= end_time "
                          "AND break_end > break_start)",
                           name="ck_doctor_schedules_break_valid"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column( ForeignKey("doctors.id"), index=True, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    break_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    doctor = relationship("Doctor", back_populates="schedules")