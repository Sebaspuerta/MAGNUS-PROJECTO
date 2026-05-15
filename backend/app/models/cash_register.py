from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CashRegister(Base):
    __tablename__ = "cash_registers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opened_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    opening_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    closed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closing_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    opened_by = relationship("User", foreign_keys=[opened_by_user_id])
    closed_by = relationship("User", foreign_keys=[closed_by_user_id])
    movements = relationship("CashMovement", back_populates="cash_register", cascade="all, delete-orphan")
