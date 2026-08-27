from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryEntryCreate,
    InventoryMovementResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate
)
from app.services.inventory_service import (
    create_inventory_adjustment,
    create_inventory_entry,
    create_product,
    deactivate_product,
    delete_product,
    get_product_by_id,
    list_product_movements,
    list_products,
    save_product_photo,
    update_product
)
from app.utils.security import require_admin, require_owner, require_permission


router = APIRouter(
    prefix="/api/inventory/products",
    tags=["Inventario"]
)


@router.get("", response_model=list[ProductResponse])
def get_products(
    include_inactive: bool = False,
    category_id: int | None = None,
    uncategorized: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ver"))
):
    return list_products(db, include_inactive=include_inactive, category_id=category_id, uncategorized=uncategorized)


@router.post("", response_model=ProductResponse)
def post_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.crear"))
):
    result, error = create_product(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ver"))
):
    result, error = get_product_by_id(db, product_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.patch("/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.editar"))
):
    result, error = update_product(db, product_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{product_id}/deactivate", response_model=ProductResponse)
def patch_deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.eliminar"))
):
    result, error = deactivate_product(db, product_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.delete("/{product_id}")
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    result, error = delete_product(db, product_id, current_user)

    if error:
        if isinstance(error, dict):
            raise HTTPException(status_code=409, detail=error)
        raise HTTPException(status_code=404, detail=error)

    return result


@router.post("/{product_id}/photo", response_model=ProductResponse)
def post_product_photo(
    product_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    file_bytes = photo.file.read()
    result, error = save_product_photo(db, product_id, file_bytes, current_user)

    if error:
        status_code = 404 if error == "Producto no encontrado." else 400
        raise HTTPException(status_code=status_code, detail=error)

    return result


@router.post("/{product_id}/entry", response_model=ProductResponse)
def post_inventory_entry(
    product_id: int,
    payload: InventoryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ajustar"))
):
    result, error = create_inventory_entry(db, product_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.post("/{product_id}/adjustment", response_model=ProductResponse)
def post_inventory_adjustment(
    product_id: int,
    payload: InventoryAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ajustar"))
):
    result, error = create_inventory_adjustment(db, product_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.get("/{product_id}/movements", response_model=list[InventoryMovementResponse])
def get_product_movements(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ver"))
):
    result, error = list_product_movements(db, product_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result
