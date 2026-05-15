from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.cash_movement import CashMovementCreate, CashMovementResponse
from app.services.cash_movement_service import create_cash_movement, list_cash_movements
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/cash-movements",
    tags=["Movimientos de Caja"]
)


@router.get("", response_model=list[CashMovementResponse])
def get_cash_movements(
    cash_register_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.ver"))
):
    return list_cash_movements(db, cash_register_id=cash_register_id)


@router.post("", response_model=CashMovementResponse)
def post_cash_movement(
    payload: CashMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.movimiento"))
):
    result, error = create_cash_movement(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result
