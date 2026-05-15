from datetime import datetime
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    alert_type: str
    message: str
    reference_type: str | None = None
    reference_id: int | None = None


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    reference_type: str | None = None
    reference_id: int | None = None
    is_read: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
