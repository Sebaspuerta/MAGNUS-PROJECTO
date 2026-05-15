from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    cash_register_id: Mapped[int | None] = mapped_column(ForeignKey("cash_registers.id"), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order = relationship("Order", back_populates="payments")
    user = relationship("User")
    cash_register = relationship("CashRegister")
