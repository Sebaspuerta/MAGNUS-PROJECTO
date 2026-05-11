from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    price: float
    estimated_duration_minutes: int | None = None
    uses_internal_consumables: bool = False


class ServiceUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = None
    estimated_duration_minutes: int | None = None
    uses_internal_consumables: bool | None = None
    is_active: bool | None = None


class ServiceResponse(BaseModel):
    id: int
    name: str
    category: str | None = None
    description: str | None = None
    price: float
    estimated_duration_minutes: int | None = None
    uses_internal_consumables: bool
    is_active: bool

    class Config:
        from_attributes = True
