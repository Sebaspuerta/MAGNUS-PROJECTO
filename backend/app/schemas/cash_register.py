from datetime import datetime
from pydantic import BaseModel, Field


class CashRegisterOpenRequest(BaseModel):
    opening_amount: float = Field(..., ge=0)
    notes: str | None = None


class CashRegisterCloseRequest(BaseModel):
    closing_amount: float = Field(..., ge=0)
    notes: str | None = None


class CashRegisterResponse(BaseModel):
    id: int
    opened_by_user_id: int
    opened_at: datetime
    opening_amount: float
    closed_by_user_id: int | None = None
    closed_at: datetime | None = None
    closing_amount: float | None = None
    is_closed: bool
    notes: str | None = None
    expected_amount: float | None = None
    difference: float | None = None

    class Config:
        from_attributes = True
