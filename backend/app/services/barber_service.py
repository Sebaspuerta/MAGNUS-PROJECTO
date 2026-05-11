from datetime import datetime
from sqlalchemy.orm import Session

from app.models.barber import Barber
from app.models.security import User
from app.schemas.barber import BarberCreate, BarberUpdate
from app.services.security_service import create_audit_log
from app.utils.security import hash_password


def serialize_barber(barber: Barber):
    return {
        "id": barber.id,
        "full_name": barber.full_name,
        "alias": barber.alias,
        "phone": barber.phone,
        "user_username": barber.user.username if barber.user else None,
        "commission_type": barber.commission_type,
        "commission_value": float(barber.commission_value or 0),
        "notes": barber.notes,
        "is_active": barber.is_active
    }


def list_barbers(db: Session, include_inactive: bool = False):
    query = db.query(Barber).order_by(Barber.id.asc())

    if not include_inactive:
        query = query.filter(Barber.is_active == True)

    return [serialize_barber(barber) for barber in query.all()]


def get_barber_by_id(db: Session, barber_id: int):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()

    if not barber:
        return None, "Barbero no encontrado."

    return serialize_barber(barber), None


def get_user_by_username(db: Session, username: str | None):
    if not username:
        return None, None

    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None, "El usuario indicado no existe."

    return user, None


def create_barber(db: Session, payload: BarberCreate, admin_user: User):
    user, error = get_user_by_username(db, payload.user_username)

    if error:
        return None, error

    if user:
        existing_barber_for_user = db.query(Barber).filter(Barber.user_id == user.id).first()
        if existing_barber_for_user:
            return None, "Ese usuario ya está vinculado a otro barbero."

    barber = Barber(
        user_id=user.id if user else None,
        full_name=payload.full_name,
        alias=payload.alias,
        phone=payload.phone,
        quick_pin_hash=hash_password(payload.quick_pin) if payload.quick_pin else None,
        commission_type=payload.commission_type,
        commission_value=payload.commission_value,
        notes=payload.notes,
        is_active=True
    )

    db.add(barber)
    db.flush()

    create_audit_log(
        db=db,
        module="barberos",
        action="crear_barbero",
        detail=f"El administrador {admin_user.username} creó el barbero {barber.full_name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(barber)

    return serialize_barber(barber), None


def update_barber(db: Session, barber_id: int, payload: BarberUpdate, admin_user: User):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()

    if not barber:
        return None, "Barbero no encontrado."

    if payload.user_username is not None:
        user, error = get_user_by_username(db, payload.user_username)

        if error:
            return None, error

        if user:
            existing_barber_for_user = (
                db.query(Barber)
                .filter(Barber.user_id == user.id, Barber.id != barber.id)
                .first()
            )

            if existing_barber_for_user:
                return None, "Ese usuario ya está vinculado a otro barbero."

        barber.user_id = user.id if user else None

    if payload.full_name is not None:
        barber.full_name = payload.full_name

    if payload.alias is not None:
        barber.alias = payload.alias

    if payload.phone is not None:
        barber.phone = payload.phone

    if payload.quick_pin is not None:
        barber.quick_pin_hash = hash_password(payload.quick_pin) if payload.quick_pin else None

    if payload.commission_type is not None:
        barber.commission_type = payload.commission_type

    if payload.commission_value is not None:
        barber.commission_value = payload.commission_value

    if payload.notes is not None:
        barber.notes = payload.notes

    if payload.is_active is not None:
        barber.is_active = payload.is_active

    barber.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="barberos",
        action="editar_barbero",
        detail=f"El administrador {admin_user.username} editó el barbero {barber.full_name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(barber)

    return serialize_barber(barber), None


def deactivate_barber(db: Session, barber_id: int, admin_user: User):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()

    if not barber:
        return None, "Barbero no encontrado."

    barber.is_active = False
    barber.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="barberos",
        action="desactivar_barbero",
        detail=f"El administrador {admin_user.username} desactivó el barbero {barber.full_name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(barber)

    return serialize_barber(barber), None
