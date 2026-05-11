from datetime import date
from pydantic import BaseModel


class ClientCreate(BaseModel):
    full_name: str
    phone: str | None = None
    email: str | None = None
    document_number: str | None = None
    birth_date: date | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    document_number: str | None = None
    birth_date: date | None = None
    notes: str | None = None
    is_active: bool | None = None


class ClientResponse(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    email: str | None = None
    document_number: str | None = None
    birth_date: date | None = None
    notes: str | None = None
    is_active: bool

    class Config:
        from_attributes = True
