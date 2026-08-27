from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int | None
    name: str
    is_deleted: bool = False
    product_count: int = 0

    class Config:
        from_attributes = True