from datetime import datetime
from sqlalchemy.orm import Session

from app.models.accounts_receivable import AccountsReceivable, AccountsReceivablePayment
from app.models.security import User
from app.models.order import Order
from app.models.client import Client
from app.schemas.accounts_receivable import AccountsReceivableCreate, AccountsReceivablePaymentCreate
from app.services.security_service import create_audit_log


def serialize_accounts_receivable(ar: AccountsReceivable):
    return {
        "id": ar.id,
        "client_id": ar.client_id,
        "order_id": ar.order_id,
        "created_by_user_id": ar.created_by_user_id,
        "total_amount": float(ar.total_amount or 0),
        "paid_amount": float(ar.paid_amount or 0),
        "balance": float(ar.balance or 0),
        "status": ar.status,
        "due_date": ar.due_date,
        "notes": ar.notes,
        "is_active": ar.is_active,
        "created_at": ar.created_at,
        "updated_at": ar.updated_at,
        "payments": [serialize_accounts_receivable_payment(payment) for payment in ar.payments]
    }


def serialize_accounts_receivable_payment(payment: AccountsReceivablePayment):
    return {
        "id": payment.id,
        "accounts_receivable_id": payment.accounts_receivable_id,
        "user_id": payment.user_id,
        "amount": float(payment.amount or 0),
        "payment_method": payment.payment_method,
        "note": payment.note,
        "payment_date": payment.payment_date
    }


def list_accounts_receivable(db: Session, client_id: int | None = None):
    query = db.query(AccountsReceivable).order_by(AccountsReceivable.id.asc())
    if client_id is not None:
        query = query.filter(AccountsReceivable.client_id == client_id)
    return [serialize_accounts_receivable(ar) for ar in query.all()]


def get_accounts_receivable_by_id(db: Session, ar_id: int):
    ar = db.query(AccountsReceivable).filter(AccountsReceivable.id == ar_id).first()
    if not ar:
        return None, "Cuenta por cobrar no encontrada."
    return serialize_accounts_receivable(ar), None


def create_accounts_receivable(db: Session, payload: AccountsReceivableCreate, current_user: User):
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        return None, "Cliente no encontrado."

    if payload.order_id is not None:
        order = db.query(Order).filter(Order.id == payload.order_id).first()
        if not order:
            return None, "Comanda no encontrada."
    else:
        order = None

    ar = AccountsReceivable(
        client_id=payload.client_id,
        order_id=payload.order_id,
        created_by_user_id=current_user.id,
        total_amount=payload.total_amount,
        paid_amount=0,
        balance=payload.total_amount,
        status="pendiente",
        due_date=payload.due_date,
        notes=payload.notes,
        is_active=True
    )

    db.add(ar)
    db.flush()

    create_audit_log(
        db=db,
        module="cuentas_por_cobrar",
        action="crear_cuenta_por_cobrar",
        detail=f"El usuario {current_user.username} creó la cuenta por cobrar {ar.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(ar)
    return serialize_accounts_receivable(ar), None


def add_accounts_receivable_payment(db: Session, ar_id: int, payload: AccountsReceivablePaymentCreate, current_user: User):
    ar = db.query(AccountsReceivable).filter(AccountsReceivable.id == ar_id).first()
    if not ar:
        return None, "Cuenta por cobrar no encontrada."

    payment = AccountsReceivablePayment(
        accounts_receivable_id=ar.id,
        user_id=current_user.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        note=payload.note
    )

    db.add(payment)
    db.flush()

    ar.paid_amount = float(ar.paid_amount or 0) + float(payload.amount)
    ar.balance = float(ar.total_amount or 0) - float(ar.paid_amount or 0)
    ar.status = "pagado" if ar.balance <= 0 else "pendiente"
    ar.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="cuentas_por_cobrar",
        action="abonar_cuenta_por_cobrar",
        detail=f"El usuario {current_user.username} registró un pago a cuenta por cobrar {ar.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(ar)
    return serialize_accounts_receivable(ar), None
