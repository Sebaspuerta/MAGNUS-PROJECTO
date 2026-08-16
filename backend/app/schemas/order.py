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
    display_name: str | None = None
    is_deleted_reference: bool = False
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    client_id: int | None = None
    barber_id: int | None = None
    is_fiado: bool = False
    notes: str | None = None
    discount: float = 0


class OrderCloseRequest(BaseModel):
    barber_id: int | None = None
    cash_register_id: int | None = None
    payment_amount: float | None = None
    payment_method: str | None = None
    note: str | None = None


class OrderQuickRegisterCreate(BaseModel):
    tipo: str = Field(..., description="corte o producto")
    barber_id: int
    service_id: int | None = None
    product_id: int | None = None
    quantity: int = Field(1, gt=0)
    payment_method: str
    payment_amount: float | None = None
    cash_register_id: int | None = None
    note: str | None = None


class OrderResponse(BaseModel):
    id: int
    client_id: int | None = None
    barber_id: int | None = None
    barber_name: str | None = None
    barber_is_deleted: bool = False
    status: str
    payment_status: str
    amount_paid: float
    is_fiado: bool
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
