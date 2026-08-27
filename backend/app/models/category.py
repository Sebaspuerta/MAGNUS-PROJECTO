from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # No unique=True aquí: el nombre solo debe ser único entre categorías VIVAS
    # (ver el índice único parcial abajo). Una categoría eliminada conserva su
    # nombre para el historial, y ese nombre debe poder reutilizarse.
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    products = relationship("Product", back_populates="category_ref")

    __table_args__ = (
        Index(
            "ix_categories_name_active_unique",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
    )