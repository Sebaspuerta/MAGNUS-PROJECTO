from datetime import datetime
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.order import Order
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.models.security import User
from app.schemas.payment import PaymentCreate
from app.services.security_service import create_audit_log


def serialize_payment(payment: Payment):
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "user_id": payment.user_id,
        "cash_register_id": payment.cash_register_id,
        "payment_method": payment.payment_method,
        "amount": float(payment.amount or 0),
        "note": payment.note,
        "paid_at": payment.paid_at
    }


def list_payments(db: Session, order_id: int | None = None):
    query = db.query(Payment).order_by(Payment.id.asc())
    if order_id is not None:
        query = query.filter(Payment.order_id == order_id)
    return [serialize_payment(payment) for payment in query.all()]


def create_payment(db: Session, payload: PaymentCreate, current_user: User):
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    if order.status == "cancelada":
        return None, "No se puede registrar el pago de una comanda cancelada."

    if payload.cash_register_id is not None:
        cash_register = db.query(CashRegister).filter(CashRegister.id == payload.cash_register_id).first()
        if not cash_register:
            return None, "Caja no encontrada."
        if cash_register.is_closed:
            return None, "La caja indicada está cerrada."
    else:
        cash_register = None

    payment = Payment(
        order_id=order.id,
        user_id=current_user.id,
        cash_register_id=payload.cash_register_id,
        payment_method=payload.payment_method,
        amount=payload.amount,
        note=payload.note
    )

    db.add(payment)
    db.flush()

    order.amount_paid = float(order.amount_paid or 0) + float(payload.amount)
    order.payment_status = "pagado" if float(order.amount_paid or 0) >= float(order.total or 0) else "parcial"
    order.updated_at = datetime.utcnow()

    if cash_register is not None:
        movement = CashMovement(
            cash_register_id=cash_register.id,
            user_id=current_user.id,
            movement_type="pago",
            amount=payload.amount,
            payment_method=payload.payment_method,
            description=f"Pago de comanda {order.id}.",
            reference_type="order",
            reference_id=order.id
        )
        db.add(movement)

    create_audit_log(
        db=db,
        module="caja",
        action="registrar_pago",
        detail=f"El usuario {current_user.username} registró pago de {payload.amount} para la comanda {order.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(payment)
    db.refresh(order)

    return serialize_payment(payment), None
