from datetime import datetime
from sqlalchemy.orm import Session

from app.models.alerts import Alert
from app.models.security import User
from app.schemas.alert import AlertCreate
from app.services.security_service import create_audit_log


def serialize_alert(alert: Alert):
    return {
        "id": alert.id,
        "alert_type": alert.alert_type,
        "message": alert.message,
        "reference_type": alert.reference_type,
        "reference_id": alert.reference_id,
        "is_read": alert.is_read,
        "is_active": alert.is_active,
        "created_at": alert.created_at
    }


def list_alerts(db: Session, only_active: bool = True):
    query = db.query(Alert).order_by(Alert.id.asc())
    if only_active:
        query = query.filter(Alert.is_active == True)
    return [serialize_alert(alert) for alert in query.all()]


def create_alert(db: Session, payload: AlertCreate, current_user: User):
    alert = Alert(
        alert_type=payload.alert_type,
        message=payload.message,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        is_read=False,
        is_active=True
    )
    db.add(alert)
    db.flush()

    create_audit_log(
        db=db,
        module="alertas",
        action="crear_alerta",
        detail=f"El usuario {current_user.username} creó la alerta {alert.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(alert)
    return serialize_alert(alert), None


def mark_alert_as_read(db: Session, alert_id: int, current_user: User):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None, "Alerta no encontrada."

    alert.is_read = True
    db.commit()
    db.refresh(alert)

    create_audit_log(
        db=db,
        module="alertas",
        action="leer_alerta",
        detail=f"El usuario {current_user.username} marcó la alerta {alert.id} como leída.",
        user_id=current_user.id
    )

    return serialize_alert(alert), None


def _alert_exists(db: Session, alert_type: str, reference_type: str, reference_id: int):
    return (
        db.query(Alert)
        .filter(
            Alert.alert_type == alert_type,
            Alert.reference_type == reference_type,
            Alert.reference_id == reference_id,
            Alert.is_active == True,  # noqa: E712
            Alert.is_read == False  # noqa: E712
        )
        .first()
        is not None
    )


def generate_system_alerts(db: Session, current_user: User):
    """Escanea inventario y cuentas por cobrar y crea alertas automáticas,
    evitando duplicar alertas activas no leídas para la misma referencia."""
    from datetime import date, timedelta
    from app.models.inventory import Product
    from app.models.accounts_receivable import AccountsReceivable

    created = 0

    # --- Inventario: agotado, stock bajo y por vencer ---
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa: E712
    expiring_limit = date.today() + timedelta(days=30)

    for product in products:
        if product.current_stock <= 0:
            if not _alert_exists(db, "stock_agotado", "product", product.id):
                db.add(Alert(
                    alert_type="stock_agotado",
                    message=f"El producto '{product.name}' está agotado.",
                    reference_type="product",
                    reference_id=product.id,
                    is_read=False,
                    is_active=True
                ))
                created += 1
        elif product.minimum_stock is not None and product.current_stock <= product.minimum_stock:
            if not _alert_exists(db, "stock_bajo", "product", product.id):
                db.add(Alert(
                    alert_type="stock_bajo",
                    message=f"El producto '{product.name}' tiene stock bajo ({product.current_stock}).",
                    reference_type="product",
                    reference_id=product.id,
                    is_read=False,
                    is_active=True
                ))
                created += 1

        if product.expiration_date is not None and product.expiration_date <= expiring_limit:
            if not _alert_exists(db, "producto_por_vencer", "product", product.id):
                db.add(Alert(
                    alert_type="producto_por_vencer",
                    message=f"El producto '{product.name}' vence el {product.expiration_date}.",
                    reference_type="product",
                    reference_id=product.id,
                    is_read=False,
                    is_active=True
                ))
                created += 1

    # --- Cuentas por cobrar vencidas ---
    today = date.today()
    overdue = (
        db.query(AccountsReceivable)
        .filter(
            AccountsReceivable.is_active == True,  # noqa: E712
            AccountsReceivable.balance > 0,
            AccountsReceivable.due_date.isnot(None),
            AccountsReceivable.due_date < today
        )
        .all()
    )
    for ar in overdue:
        if not _alert_exists(db, "deuda_vencida", "accounts_receivable", ar.id):
            db.add(Alert(
                alert_type="deuda_vencida",
                message=f"La cuenta por cobrar {ar.id} está vencida (saldo {float(ar.balance or 0)}).",
                reference_type="accounts_receivable",
                reference_id=ar.id,
                is_read=False,
                is_active=True
            ))
            created += 1

    create_audit_log(
        db=db,
        module="alertas",
        action="generar_alertas",
        detail=f"El usuario {current_user.username} generó {created} alertas automáticas.",
        user_id=current_user.id
    )

    db.commit()
    return {"created": created}, None
