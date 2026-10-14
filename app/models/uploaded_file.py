from enum import Enum

from sqlalchemy import ( CheckConstraint,Enum as SQLAlchemyEnum,ForeignKey,
                         Integer,String )
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FileType(str, Enum):
    LAB_REPORT = "Lab Report"
    PRESCRIPTION = "Prescription"
    SCAN = "Scan"


class UploadedFile(TimestampMixin, Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        CheckConstraint(
            "size_kb > 0 AND size_kb <= 5120",
            name="ck_uploaded_files_size",
        ),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column( ForeignKey("appointments.id"), index=True,nullable=False)
    uploaded_by: Mapped[int] = mapped_column( ForeignKey("users.id"),nullable=False )
    file_type: Mapped[FileType] = mapped_column(SQLAlchemyEnum(FileType,values_callable=lambda enum_type:
                                                               [item.value for item in enum_type],native_enum=False,length=20 ),nullable=False )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column( String(255),unique=True,nullable=False)
    size_kb: Mapped[int] = mapped_column(Integer, nullable=False)

    appointment = relationship("Appointment", back_populates="files")
    uploader = relationship("User", back_populates="uploaded_files")