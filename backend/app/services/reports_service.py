from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.barber import Barber
from app.models.inventory import Product
from app.models.accounts_receivable import AccountsReceivable
from app.models.cash_register import CashRegister
from app.models.client import Client


def _resolve_range(start_date, end_date):
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    start_dt = datetime(start_date.year, start_date.month, start_date.day)
    end_dt = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)
    return start_date, end_date, start_dt, end_dt


def sales_by_period(db: Session, start_date=None, end_date=None):
    start_date, end_date, start_dt, end_dt = _resolve_range(start_date, end_date)

    rows = (
        db.query(
            func.date(Order.closed_at).label("day"),
            func.count(Order.id).label("orders_count"),
            func.coalesce(func.sum(Order.total), 0).label("sales_total")
        )
        .filter(Order.status == "cerrada", Order.closed_at >= start_dt, Order.closed_at < end_dt)
        .group_by(func.date(Order.closed_at))
        .order_by(func.date(Order.closed_at))
        .all()
    )

    days = [
        {"date": str(r.day), "orders_count": int(r.orders_count or 0), "sales_total": float(r.sales_total or 0)}
        for r in rows
    ]
    total_sales = sum(d["sales_total"] for d in days)
    total_orders = sum(d["orders_count"] for d in days)

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "total_sales": round(total_sales, 2),
        "total_orders": total_orders,
        "days": days
    }


def sales_by_barber(db: Session, start_date=None, end_date=None):
    start_date, end_date, start_dt, end_dt = _resolve_range(start_date, end_date)

    rows = (
        db.query(
            Order.barber_id,
            func.count(Order.id).label("orders_count"),
            func.coalesce(func.sum(Order.total), 0).label("sales_total")
        )
        .filter(Order.status == "cerrada", Order.closed_at >= start_dt, Order.closed_at < end_dt)
        .group_by(Order.barber_id)
        .all()
    )

    result = []
    for r in rows:
        barber = db.query(Barber).filter(Barber.id == r.barber_id).first() if r.barber_id else None
        sales_total = float(r.sales_total or 0)
        orders_count = int(r.orders_count or 0)

        commission_type = (barber.commission_type or "").lower() if barber else ""
        commission_value = float(barber.commission_value or 0) if barber else 0.0
        if commission_type in ("porcentaje", "percent", "%"):
            commission = sales_total * commission_value / 100.0
        elif commission_type in ("fijo", "fixed", "monto"):
            commission = commission_value * orders_count
        else:
            commission = 0.0

        result.append({
            "barber_id": r.barber_id,
            "barber_name": barber.full_name if barber else "Sin barbero",
            "orders_count": orders_count,
            "sales_total": round(sales_total, 2),
            "estimated_commission": round(commission, 2)
        })

    result.sort(key=lambda x: x["sales_total"], reverse=True)
    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "barbers": result
    }


def top_products(db: Session, start_date=None, end_date=None, limit: int = 10):
    start_date, end_date, start_dt, end_dt = _resolve_range(start_date, end_date)

    rows = (
        db.query(
            OrderItem.product_id,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(OrderItem.total_price), 0).label("revenue")
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.status == "cerrada",
            Order.closed_at >= start_dt,
            Order.closed_at < end_dt,
            OrderItem.item_type == "producto",
            OrderItem.product_id.isnot(None)
        )
        .group_by(OrderItem.product_id)
        .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
        .limit(limit)
        .all()
    )

    products = []
    for r in rows:
        product = db.query(Product).filter(Product.id == r.product_id).first()
        products.append({
            "product_id": r.product_id,
            "product_name": product.name if product else "Producto eliminado",
            "quantity_sold": int(r.qty or 0),
            "revenue": round(float(r.revenue or 0), 2)
        })

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "products": products
    }


def accounts_receivable_report(db: Session):
    today = date.today()
    rows = (
        db.query(AccountsReceivable)
        .filter(AccountsReceivable.is_active == True, AccountsReceivable.balance > 0)  # noqa: E712
        .order_by(AccountsReceivable.balance.desc())
        .all()
    )

    items = []
    for ar in rows:
        client = db.query(Client).filter(Client.id == ar.client_id).first()
        is_overdue = ar.due_date is not None and ar.due_date < today
        items.append({
            "id": ar.id,
            "client_id": ar.client_id,
            "client_name": client.full_name if client else None,
            "total_amount": float(ar.total_amount or 0),
            "paid_amount": float(ar.paid_amount or 0),
            "balance": float(ar.balance or 0),
            "status": ar.status,
            "due_date": ar.due_date,
            "is_overdue": is_overdue
        })

    total_balance = sum(i["balance"] for i in items)
    overdue_balance = sum(i["balance"] for i in items if i["is_overdue"])

    return {
        "generated_at": date.today(),
        "count": len(items),
        "total_balance": round(total_balance, 2),
        "overdue_balance": round(overdue_balance, 2),
        "items": items
    }


def cash_closings(db: Session, start_date=None, end_date=None):
    start_date, end_date, start_dt, end_dt = _resolve_range(start_date, end_date)

    registers = (
        db.query(CashRegister)
        .filter(
            CashRegister.is_closed == True,  # noqa: E712
            CashRegister.closed_at >= start_dt,
            CashRegister.closed_at < end_dt
        )
        .order_by(CashRegister.closed_at.desc())
        .all()
    )

    items = []
    for reg in registers:
        received = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.cash_register_id == reg.id)
            .scalar()
        )
        expected = float(reg.opening_amount or 0) + float(received or 0)
        counted = float(reg.closing_amount or 0)
        items.append({
            "id": reg.id,
            "opened_at": reg.opened_at,
            "closed_at": reg.closed_at,
            "opening_amount": float(reg.opening_amount or 0),
            "received": float(received or 0),
            "expected_amount": round(expected, 2),
            "closing_amount": counted,
            "difference": round(counted - expected, 2)
        })

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "count": len(items),
        "closings": items
    }
