from datetime import datetime
from pydantic import BaseModel, Field


class CashMovementCreate(BaseModel):
    cash_register_id: int
    movement_type: str
    amount: float = Field(..., gt=0)
    payment_method: str | None = None
    description: str
    reference_type: str | None = None
    reference_id: int | None = None


class CashMovementResponse(BaseModel):
    id: int
    cash_register_id: int
    user_id: int
    movement_type: str
    amount: float
    payment_method: str | None = None
    description: str
    reference_type: str | None = None
    reference_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
