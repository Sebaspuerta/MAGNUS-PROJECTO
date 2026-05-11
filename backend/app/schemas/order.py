from datetime import datetime
from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    item_type: str = Field(..., description="servicio o producto")
    service_id: int | None = None
    product_id: int | None = None
    description: str | None = None
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class OrderItemUpdate(BaseModel):
    quantity: int | None = Field(None, gt=0)
    unit_price: float | None = Field(None, ge=0)
    description: str | None = None


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    item_type: str
    service_id: int | None = None
    product_id: int | None = None
    description: str | None = None
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    client_id: int | None = None
    barber_id: int | None = None
    notes: str | None = None
    discount: float = 0


class OrderResponse(BaseModel):
    id: int
    client_id: int | None = None
    barber_id: int | None = None
    status: str
    subtotal: float
    discount: float
    total: float
    notes: str | None = None
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True
