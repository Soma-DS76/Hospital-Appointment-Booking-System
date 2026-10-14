from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DoctorLeave(TimestampMixin, Base):
    __tablename__ = "doctor_leaves"
    __table_args__ = (
        CheckConstraint(
            "end_date >= start_date",
            name="ck_doctor_leaves_end_after_start",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column( ForeignKey("doctors.id"), index=True, nullable=False )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    doctor = relationship("Doctor", back_populates="leaves")