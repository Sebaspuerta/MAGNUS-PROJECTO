from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import create_payment, list_payments
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/payments",
    tags=["Pagos"]
)


@router.get("", response_model=list[PaymentResponse])
def get_payments(
    order_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.ver"))
):
    return list_payments(db, order_id=order_id)


@router.post("", response_model=PaymentResponse)
def post_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("caja.movimiento"))
):
    result, error = create_payment(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result
