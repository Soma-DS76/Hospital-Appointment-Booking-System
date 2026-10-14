from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import Date, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from datetime import date


class Consultation(TimestampMixin, Base):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column( ForeignKey("appointments.id"),unique=True,nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    prescription: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column( JSON, nullable=True )
    advice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    appointment = relationship("Appointment", back_populates="consultation")