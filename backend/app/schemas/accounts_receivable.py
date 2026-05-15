from datetime import date, datetime
from pydantic import BaseModel, Field


class AccountsReceivableCreate(BaseModel):
    client_id: int
    order_id: int | None = None
    total_amount: float = Field(..., gt=0)
    due_date: date | None = None
    notes: str | None = None


class AccountsReceivablePaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str | None = None
    note: str | None = None


class AccountsReceivablePaymentResponse(BaseModel):
    id: int
    accounts_receivable_id: int
    user_id: int
    amount: float
    payment_method: str | None = None
    note: str | None = None
    payment_date: datetime

    class Config:
        from_attributes = True


class AccountsReceivableResponse(BaseModel):
    id: int
    client_id: int
    order_id: int | None = None
    created_by_user_id: int
    total_amount: float
    paid_amount: float
    balance: float
    status: str
    due_date: date | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    payments: list[AccountsReceivablePaymentResponse] = []

    class Config:
        from_attributes = True
