from datetime import date, datetime
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str
    category_id: int | None = None
    product_type: str
    description: str | None = None
    purchase_cost: float = Field(0, ge=0)
    sale_price: float = Field(0, ge=0)
    current_stock: int = Field(0, ge=0)
    minimum_stock: int | None = Field(None, ge=0)
    expiration_date: date | None = None
    supplier: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: int | None = None
    product_type: str | None = None
    description: str | None = None
    purchase_cost: float | None = Field(None, ge=0)
    sale_price: float | None = Field(None, ge=0)
    current_stock: int | None = Field(None, ge=0)
    minimum_stock: int | None = Field(None, ge=0)
    expiration_date: date | None = None
    supplier: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    category_id: int | None = None
    category_name: str | None = None
    category_is_deleted: bool = False
    product_type: str
    description: str | None = None
    purchase_cost: float
    sale_price: float
    current_stock: int
    minimum_stock: int | None = None
    expiration_date: date | None = None
    supplier: str | None = None
    is_active: bool
    is_deleted: bool = False
    photo_filename: str | None = None
    photo_url: str | None = None

    class Config:
        from_attributes = True


class InventoryEntryCreate(BaseModel):
    quantity: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1)


class InventoryAdjustmentCreate(BaseModel):
    quantity: int
    reason: str = Field(..., min_length=1)


class InventoryMovementResponse(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: int
    previous_stock: int
    new_stock: int
    reason: str
    reference_type: str | None = None
    reference_id: int | None = None
    created_by_user_id: int
    created_at: datetime

    class Config:
        from_attributes = True