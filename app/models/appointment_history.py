from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.appointment import AppointmentStatus
from app.models.base import Base, TimestampMixin


class AppointmentHistory(TimestampMixin, Base):
    __tablename__ = "appointment_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column( ForeignKey("appointments.id"), index=True,nullable=False )
    old_status: Mapped[AppointmentStatus] = mapped_column(nullable=False)
    new_status: Mapped[AppointmentStatus] = mapped_column(nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column( ForeignKey("users.id"),nullable=True )
    changed_at: Mapped[datetime] = mapped_column( DateTime(timezone=True),server_default=func.now(),nullable=False)

    appointment = relationship("Appointment", back_populates="history")