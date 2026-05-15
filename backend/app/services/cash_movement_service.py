from datetime import datetime
from sqlalchemy.orm import Session

from app.models.cash_movement import CashMovement
from app.models.cash_register import CashRegister
from app.models.security import User
from app.schemas.cash_movement import CashMovementCreate
from app.services.security_service import create_audit_log


def serialize_cash_movement(movement: CashMovement):
    return {
        "id": movement.id,
        "cash_register_id": movement.cash_register_id,
        "user_id": movement.user_id,
        "movement_type": movement.movement_type,
        "amount": float(movement.amount or 0),
        "payment_method": movement.payment_method,
        "description": movement.description,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "created_at": movement.created_at
    }


def list_cash_movements(db: Session, cash_register_id: int | None = None):
    query = db.query(CashMovement).order_by(CashMovement.id.asc())
    if cash_register_id is not None:
        query = query.filter(CashMovement.cash_register_id == cash_register_id)
    return [serialize_cash_movement(movement) for movement in query.all()]


def create_cash_movement(db: Session, payload: CashMovementCreate, current_user: User):
    cash_register = db.query(CashRegister).filter(CashRegister.id == payload.cash_register_id).first()
    if not cash_register:
        return None, "Caja no encontrada."

    if cash_register.is_closed:
        return None, "La caja indicada está cerrada."

    movement = CashMovement(
        cash_register_id=payload.cash_register_id,
        user_id=current_user.id,
        movement_type=payload.movement_type,
        amount=payload.amount,
        payment_method=payload.payment_method,
        description=payload.description,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id
    )

    db.add(movement)
    db.flush()

    create_audit_log(
        db=db,
        module="caja",
        action="movimiento_caja",
        detail=f"El usuario {current_user.username} registró un movimiento de caja {movement.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(movement)
    return serialize_cash_movement(movement), None
