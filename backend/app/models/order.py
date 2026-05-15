from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True)
    barber_id: Mapped[int | None] = mapped_column(ForeignKey("barbers.id"), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    is_fiado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="abierta")
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client = relationship("Client")
    barber = relationship("Barber")
    created_by = relationship("User")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    service = relationship("Service")
    product = relationship("Product")
