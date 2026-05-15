from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderItemUpdate
)
from app.services.order_service import (
    add_order_item,
    cancel_order,
    close_order,
    create_order,
    delete_order_item,
    get_order_by_id,
    list_orders,
    mark_order_pending,
    update_order_item
)
from app.utils.security import get_current_user, require_permission


router = APIRouter(
    prefix="/api/orders",
    tags=["Comandas Digitales"]
)


@router.get("", response_model=list[OrderResponse])
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.ver"))
):
    return list_orders(db)


@router.post("", response_model=OrderResponse)
def post_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.crear"))
):
    result, error = create_order(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.ver"))
):
    result, error = get_order_by_id(db, order_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.post("/{order_id}/items", response_model=OrderResponse)
def post_order_item(
    order_id: int,
    payload: OrderItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.editar"))
):
    result, error = add_order_item(db, order_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{order_id}/items/{item_id}", response_model=OrderResponse)
def patch_order_item(
    order_id: int,
    item_id: int,
    payload: OrderItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.editar"))
):
    result, error = update_order_item(db, order_id, item_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
def delete_order_item_route(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.editar"))
):
    result, error = delete_order_item(db, order_id, item_id, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{order_id}/pending", response_model=OrderResponse)
def patch_order_pending(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.editar"))
):
    result, error = mark_order_pending(db, order_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.patch("/{order_id}/close", response_model=OrderResponse)
def patch_order_close(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.cerrar"))
):
    result, error = close_order(db, order_id, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
def patch_order_cancel(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("comandas.editar"))
):
    result, error = cancel_order(db, order_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result
