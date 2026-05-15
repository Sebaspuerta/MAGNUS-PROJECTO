from fastapi import APIRouter, Depends, HTTPException
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
    get_product_by_id,
    list_product_movements,
    list_products,
    update_product
)
from app.utils.security import get_current_user, require_permission


router = APIRouter(
    prefix="/api/inventory/products",
    tags=["Inventario"]
)


@router.get("", response_model=list[ProductResponse])
def get_products(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventario.ver"))
):
    return list_products(db, include_inactive=include_inactive)


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
    current_user: User = Depends(get_current_user)
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
