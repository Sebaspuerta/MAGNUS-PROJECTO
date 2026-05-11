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
    create_order,
    delete_order_item,
    get_order_by_id,
    list_orders,
    mark_order_pending,
    update_order_item
)
from app.utils.security import get_current_user


router = APIRouter(
    prefix="/api/orders",
    tags=["Comandas Digitales"]
)


def _require_order_edit_role(current_user: User) -> User:
    if current_user.role.name not in ["Administrador", "Barbero", "Cajero"]:
        raise HTTPException(
            status_code=403,
            detail="Solo Administrador, Barbero o Cajero pueden gestionar comandas."
        )
    return current_user


@router.get("", response_model=list[OrderResponse])
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return list_orders(db)


@router.post("", response_model=OrderResponse)
def post_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user = _require_order_edit_role(current_user)
    result, error = create_order(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    current_user = _require_order_edit_role(current_user)
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
    current_user: User = Depends(get_current_user)
):
    current_user = _require_order_edit_role(current_user)
    result, error = update_order_item(db, order_id, item_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
def delete_order_item_route(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user = _require_order_edit_role(current_user)
    result, error = delete_order_item(db, order_id, item_id, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{order_id}/pending", response_model=OrderResponse)
def patch_order_pending(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user = _require_order_edit_role(current_user)
    result, error = mark_order_pending(db, order_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
def patch_order_cancel(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user = _require_order_edit_role(current_user)
    result, error = cancel_order(db, order_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result
