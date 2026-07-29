from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.cash_register import CashRegister
from app.models.inventory import Product
from app.models.accounts_receivable import AccountsReceivable
from app.models.alerts import Alert
from app.models.barber import Barber

_BUSINESS_TZ = ZoneInfo(settings.business_tz)


def _today_bounds():
    # "Hoy" = día calendario en hora Colombia. Los timestamps en BD son UTC naivo,
    # por lo que convertimos medianoche Colombia → UTC para la comparación.
    today_col = datetime.now(_BUSINESS_TZ).date()
    midnight_col = datetime(today_col.year, today_col.month, today_col.day, tzinfo=_BUSINESS_TZ)
    start = midnight_col.astimezone(timezone.utc).replace(tzinfo=None)
    end = start + timedelta(days=1)
    return start, end


def get_dashboard_summary(db: Session):
    """Agrega en un solo objeto las cifras del día para el panel principal.
    Solo lee datos existentes; no modifica nada."""
    start, end = _today_bounds()

    # --- Ventas / comandas del día ---
    received_today = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.paid_at >= start, Payment.paid_at < end)
        .scalar()
    )
    orders_closed_today = (
        db.query(func.count(Order.id))
        .filter(Order.status == "cerrada", Order.closed_at >= start, Order.closed_at < end)
        .scalar()
    )
    orders_open = (
        db.query(func.count(Order.id))
        .filter(Order.status.in_(["abierta", "pendiente"]))
        .scalar()
    )

    # --- Caja abierta ---
    open_register = (
        db.query(CashRegister)
        .filter(CashRegister.is_closed == False)  # noqa: E712
        .order_by(CashRegister.id.desc())
        .first()
    )
    if open_register:
        received_in_register = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.cash_register_id == open_register.id,
                Payment.paid_at >= start,
                Payment.paid_at < end
            )
            .scalar()
        )
        cash = {
            "has_open_register": True,
            "open_register_id": open_register.id,
            "opening_amount": float(open_register.opening_amount or 0),
            "received_today_in_register": float(received_in_register or 0),
            "expected_amount": float(open_register.opening_amount or 0) + float(received_in_register or 0)
        }
    else:
        cash = {
            "has_open_register": False,
            "open_register_id": None,
            "opening_amount": 0.0,
            "received_today_in_register": 0.0,
            "expected_amount": 0.0
        }

    # --- Inventario ---
    out_of_stock = (
        db.query(func.count(Product.id))
        .filter(Product.is_active == True, Product.current_stock <= 0)  # noqa: E712
        .scalar()
    )
    low_stock = (
        db.query(func.count(Product.id))
        .filter(
            Product.is_active == True,  # noqa: E712
            Product.minimum_stock.isnot(None),
            Product.current_stock > 0,
            Product.current_stock <= Product.minimum_stock
        )
        .scalar()
    )
    expiring_limit = datetime.now(_BUSINESS_TZ).date() + timedelta(days=30)
    expiring_soon = (
        db.query(func.count(Product.id))
        .filter(
            Product.is_active == True,  # noqa: E712
            Product.expiration_date.isnot(None),
            Product.expiration_date <= expiring_limit
        )
        .scalar()
    )

    # --- Cuentas por cobrar ---
    pending_count = (
        db.query(func.count(AccountsReceivable.id))
        .filter(AccountsReceivable.is_active == True, AccountsReceivable.balance > 0)  # noqa: E712
        .scalar()
    )
    pending_balance = (
        db.query(func.coalesce(func.sum(AccountsReceivable.balance), 0))
        .filter(AccountsReceivable.is_active == True, AccountsReceivable.balance > 0)  # noqa: E712
        .scalar()
    )

    # --- Alertas no leídas ---
    unread_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.is_active == True, Alert.is_read == False)  # noqa: E712
        .scalar()
    )

    return {
        "generated_at": datetime.utcnow(),
        "today": {
            "received_total": float(received_today or 0),
            "orders_closed": int(orders_closed_today or 0),
            "orders_open": int(orders_open or 0)
        },
        "cash": cash,
        "inventory": {
            "out_of_stock": int(out_of_stock or 0),
            "low_stock": int(low_stock or 0),
            "expiring_soon": int(expiring_soon or 0)
        },
        "accounts_receivable": {
            "pending_count": int(pending_count or 0),
            "pending_balance": float(pending_balance or 0)
        },
        "alerts": {
            "unread": int(unread_alerts or 0)
        }
    }


def get_my_cuts_today(db: Session, user_id: int):
    """Conteo personal (sin dinero) de comandas cerradas hoy para el barbero
    vinculado al usuario autenticado. Si el usuario no tiene barbero asociado,
    devuelve 0 en lugar de fallar."""
    start, end = _today_bounds()

    barber = db.query(Barber).filter(Barber.user_id == user_id).first()
    if not barber:
        return {"cortes_hoy": 0}

    cortes_hoy = (
        db.query(func.count(Order.id))
        .filter(
            Order.barber_id == barber.id,
            Order.status == "cerrada",
            Order.closed_at >= start,
            Order.closed_at < end
        )
        .scalar()
    )

    return {"cortes_hoy": int(cortes_hoy or 0)}
