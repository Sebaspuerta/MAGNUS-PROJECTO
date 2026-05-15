from datetime import datetime
from pydantic import BaseModel, Field


class SystemConfigCreate(BaseModel):
    key: str
    value: str
    description: str | None = None


class SystemConfigUpdate(BaseModel):
    value: str | None = None
    description: str | None = None


class SystemConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
