from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.cash_register import CashRegisterCloseRequest, CashRegisterOpenRequest, CashRegisterResponse
from app.services.cash_register_service import (
    close_cash_register,
    get_cash_register_by_id,
    list_cash_registers,
    open_cash_register
)
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/cash-registers",
    tags=["Caja"]
)


@router.get("", response_model=list[CashRegisterResponse])
def get_cash_registers(
    include_closed: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.ver"))
):
    return list_cash_registers(db, include_closed=include_closed)


@router.get("/{register_id}", response_model=CashRegisterResponse)
def get_cash_register(
    register_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.ver"))
):
    result, error = get_cash_register_by_id(db, register_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result


@router.post("/open", response_model=CashRegisterResponse)
def post_open_cash_register(
    payload: CashRegisterOpenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.abrir"))
):
    result, error = open_cash_register(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.patch("/{register_id}/close", response_model=CashRegisterResponse)
def patch_close_cash_register(
    register_id: int,
    payload: CashRegisterCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.cerrar"))
):
    result, error = close_cash_register(db, register_id, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result
