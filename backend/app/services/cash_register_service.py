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
    # Nunca debe haber más de una caja abierta a la vez: si se permite, cada
    # pantalla que pregunta "¿cuál caja está abierta?" puede quedar mirando
    # una fila distinta (Dashboard toma la más reciente, otras vistas podrían
    # tomar la primera de una lista), y cerrar una deja a las demás pensando
    # que la caja sigue abierta. Se bloquea aquí, en el único punto de
    # entrada real para abrir caja, sin importar desde qué pantalla se llame.
    existing_open = (
        db.query(CashRegister)
        .filter(CashRegister.is_closed.is_(False))
        .order_by(CashRegister.id.desc())
        .first()
    )
    if existing_open:
        return None, f"Ya hay una caja abierta (#{existing_open.id}). Ciérrala antes de abrir una nueva."

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
    from sqlalchemy import func
    from app.models.payment import Payment
    from app.models.accounts_receivable import AccountsReceivablePayment

    register = db.query(CashRegister).filter(CashRegister.id == register_id).first()
    if not register:
        return None, "Caja no encontrada."

    if register.is_closed:
        return None, "La caja ya está cerrada."

    # Arqueo: efectivo físico esperado = apertura + pagos en efectivo de esta
    # caja (comandas + abonos de fiados). Nequi, Daviplata, tarjeta,
    # transferencia, cortesía y combinado no son efectivo físico y no cuentan.
    received_orders = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.cash_register_id == register.id, Payment.payment_method == "efectivo")
        .scalar()
    )
    received_ar_payments = (
        db.query(func.coalesce(func.sum(AccountsReceivablePayment.amount), 0))
        .filter(
            AccountsReceivablePayment.cash_register_id == register.id,
            AccountsReceivablePayment.payment_method == "efectivo"
        )
        .scalar()
    )
    received = float(received_orders or 0) + float(received_ar_payments or 0)
    expected_amount = float(register.opening_amount or 0) + received
    difference = float(payload.closing_amount) - expected_amount

    register.closing_amount = payload.closing_amount
    register.closed_by_user_id = current_user.id
    register.closed_at = datetime.utcnow()
    register.is_closed = True
    register.notes = payload.notes or register.notes

    create_audit_log(
        db=db,
        module="caja",
        action="cerrar_caja",
        detail=(
            f"El usuario {current_user.username} cerró la caja {register.id}. "
            f"Esperado: {expected_amount}, contado: {payload.closing_amount}, "
            f"diferencia: {round(difference, 2)}."
        ),
        user_id=current_user.id
    )

    db.commit()
    db.refresh(register)

    result = serialize_cash_register(register)
    result["expected_amount"] = round(expected_amount, 2)
    result["difference"] = round(difference, 2)
    return result, None
