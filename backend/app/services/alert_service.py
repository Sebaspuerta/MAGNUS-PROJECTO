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
