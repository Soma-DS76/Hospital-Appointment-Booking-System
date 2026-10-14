from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from typing import Optional

class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column( String(100), unique=True,index=True,
                                       nullable=False )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    doctors = relationship("Doctor", back_populates="department")