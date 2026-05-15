from datetime import datetime
from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    order_id: int
    payment_method: str
    amount: float = Field(..., gt=0)
    cash_register_id: int | None = None
    note: str | None = None


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    user_id: int
    cash_register_id: int | None = None
    payment_method: str
    amount: float
    note: str | None = None
    paid_at: datetime

    class Config:
        from_attributes = True
