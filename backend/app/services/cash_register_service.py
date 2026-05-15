from datetime import datetime
from sqlalchemy.orm import Session

from app.models.cash_register import CashRegister
from app.models.security import User
from app.schemas.cash_register import CashRegisterOpenRequest, CashRegisterCloseRequest
from app.services.security_service import create_audit_log


def serialize_cash_register(register: CashRegister):
    return {
        "id": register.id,
        "opened_by_user_id": register.opened_by_user_id,
        "opened_at": register.opened_at,
        "opening_amount": float(register.opening_amount or 0),
        "closed_by_user_id": register.closed_by_user_id,
        "closed_at": register.closed_at,
        "closing_amount": float(register.closing_amount or 0) if register.closing_amount is not None else None,
        "is_closed": register.is_closed,
        "notes": register.notes
    }


def list_cash_registers(db: Session, include_closed: bool = False):
    query = db.query(CashRegister).order_by(CashRegister.id.asc())
    if not include_closed:
        query = query.filter(CashRegister.is_closed == False)
    return [serialize_cash_register(register) for register in query.all()]


def get_cash_register_by_id(db: Session, register_id: int):
    register = db.query(CashRegister).filter(CashRegister.id == register_id).first()
    if not register:
        return None, "Caja no encontrada."
    return serialize_cash_register(register), None


def open_cash_register(db: Session, payload: CashRegisterOpenRequest, current_user: User):
    register = CashRegister(
        opened_by_user_id=current_user.id,
        opening_amount=payload.opening_amount,
        notes=payload.notes,
        is_closed=False
    )
    db.add(register)
    db.flush()

    create_audit_log(
        db=db,
        module="caja",
        action="abrir_caja",
        detail=f"El usuario {current_user.username} abrió la caja {register.id} con {payload.opening_amount}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(register)
    return serialize_cash_register(register), None


def close_cash_register(db: Session, register_id: int, payload: CashRegisterCloseRequest, current_user: User):
    register = db.query(CashRegister).filter(CashRegister.id == register_id).first()
    if not register:
        return None, "Caja no encontrada."

    if register.is_closed:
        return None, "La caja ya está cerrada."

    register.closing_amount = payload.closing_amount
    register.closed_by_user_id = current_user.id
    register.closed_at = datetime.utcnow()
    register.is_closed = True
    register.notes = payload.notes or register.notes

    create_audit_log(
        db=db,
        module="caja",
        action="cerrar_caja",
        detail=f"El usuario {current_user.username} cerró la caja {register.id} con {payload.closing_amount}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(register)
    return serialize_cash_register(register), None
