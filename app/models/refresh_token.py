from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column( ForeignKey("users.id"),index=True,nullable=False)
    token_hash: Mapped[str] = mapped_column( String(255),unique=True,index=True,nullable=False)
    expires_at: Mapped[datetime] = mapped_column( DateTime(timezone=True),nullable=False )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),nullable=True)

    user = relationship("User", back_populates="refresh_tokens")