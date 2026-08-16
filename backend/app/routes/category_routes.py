from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import create_category, delete_category, list_categories
from app.utils.security import require_owner, require_permission


router = APIRouter(
    prefix="/api/categories",
    tags=["Categorías de Inventario"]
)


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ver"))
):
    return list_categories(db)


@router.post("", response_model=CategoryResponse)
def post_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    result, error = create_category(db, payload.name, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.delete("/{category_id}")
def delete_category_endpoint(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    result, error = delete_category(db, category_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result