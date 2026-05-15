from datetime import datetime
from pydantic import BaseModel, Field


class ServiceConsumableCreate(BaseModel):
    service_id: int
    product_id: int
    quantity: int = Field(..., gt=0)


class ServiceConsumableUpdate(BaseModel):
    quantity: int | None = Field(None, gt=0)


class ServiceConsumableResponse(BaseModel):
    id: int
    service_id: int
    product_id: int
    quantity: int
    created_at: datetime

    class Config:
        from_attributes = True
