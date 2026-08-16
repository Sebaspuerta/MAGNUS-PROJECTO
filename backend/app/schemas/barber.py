from pydantic import BaseModel


class BarberCreate(BaseModel):
    full_name: str
    alias: str | None = None
    phone: str | None = None
    user_username: str | None = None
    quick_pin: str | None = None
    commission_type: str = "porcentaje"
    commission_value: float = 0
    notes: str | None = None


class BarberUpdate(BaseModel):
    full_name: str | None = None
    alias: str | None = None
    phone: str | None = None
    user_username: str | None = None
    quick_pin: str | None = None
    commission_type: str | None = None
    commission_value: float | None = None
    notes: str | None = None
    is_active: bool | None = None


class BarberResponse(BaseModel):
    id: int
    full_name: str
    alias: str | None = None
    phone: str | None = None
    has_user: bool = False
    user_username: str | None = None
    user_is_active: bool | None = None
    commission_type: str
    commission_value: float
    notes: str | None = None
    is_active: bool
    is_deleted: bool = False

    class Config:
        from_attributes = True


class BarberUserPasswordRequest(BaseModel):
    password: str
