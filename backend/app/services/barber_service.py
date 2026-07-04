import re
import unicodedata
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.barber import Barber
from app.models.security import Role, User
from app.schemas.barber import BarberCreate, BarberUpdate
from app.services.security_service import create_audit_log
from app.utils.security import hash_password


def serialize_barber(barber: Barber):
    return {
        "id": barber.id,
        "full_name": barber.full_name,
        "alias": barber.alias,
        "phone": barber.phone,
        "has_user": barber.user is not None,
        "user_username": barber.user.username if barber.user else None,
        "user_is_active": barber.user.is_active if barber.user else None,
        "commission_type": barber.commission_type,
        "commission_value": float(barber.commission_value or 0),
        "notes": barber.notes,
        "is_active": barber.is_active
    }


# ── Helpers de usuario de barbero ────────────────────────────────────────────

def _slugify_name(name: str) -> str:
    """Convierte "Mateo Pérez" → "mateo.perez"."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    slugged = re.sub(r"\s+", ".", lower.strip())
    return re.sub(r"[^a-z0-9.]", "", slugged).strip(".")


def _validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not any(c.isalpha() for c in password):
        return "La contraseña debe contener al menos una letra."
    if not any(c.isdigit() for c in password):
        return "La contraseña debe contener al menos un número."
    return None


def _generate_unique_username(db: Session, base: str) -> str:
    candidate = base
    counter = 2
    while db.query(User).filter(User.username == candidate).first():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate


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


def create_barber_user(db: Session, barber_id: int, password: str, admin_user: User):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None, "Barbero no encontrado."

    if barber.user_id:
        return None, "Este barbero ya tiene usuario de acceso. Usa reset-password para cambiar la contraseña."

    error = _validate_password(password)
    if error:
        return None, error

    base_username = _slugify_name(barber.full_name) or f"barbero{barber.id}"
    username = _generate_unique_username(db, base_username)

    barbero_role = db.query(Role).filter(Role.name == "Barbero", Role.is_active == True).first()  # noqa: E712
    if not barbero_role:
        return None, "El rol 'Barbero' no existe o está inactivo en el sistema."

    new_user = User(
        username=username,
        full_name=barber.full_name,
        password_hash=hash_password(password),
        role_id=barbero_role.id,
        is_active=True,
        must_change_password=False
    )
    db.add(new_user)
    db.flush()

    barber.user_id = new_user.id
    barber.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="barberos",
        action="crear_usuario_barbero",
        detail=f"Admin '{admin_user.username}' creó usuario '{username}' para el barbero {barber.full_name}.",
        user_id=admin_user.id
    )
    db.commit()

    return {
        "barber_id": barber.id,
        "barber_full_name": barber.full_name,
        "username": username
    }, None


def reset_barber_password(db: Session, barber_id: int, password: str, admin_user: User):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None, "Barbero no encontrado."

    if not barber.user_id:
        return None, "Este barbero no tiene usuario de acceso. Usa create-user primero."

    error = _validate_password(password)
    if error:
        return None, error

    user = db.query(User).filter(User.id == barber.user_id).first()
    if not user:
        return None, "Usuario vinculado no encontrado."

    user.password_hash = hash_password(password)
    user.password_changed_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None

    create_audit_log(
        db=db,
        module="barberos",
        action="reset_password_barbero",
        detail=f"Admin '{admin_user.username}' cambió la contraseña del usuario '{user.username}' (barbero {barber.full_name}).",
        user_id=admin_user.id
    )
    db.commit()

    return {
        "barber_id": barber.id,
        "username": user.username,
        "detail": "Contraseña actualizada correctamente."
    }, None


def toggle_barber_access(db: Session, barber_id: int, admin_user: User):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None, "Barbero no encontrado."

    if not barber.user_id:
        return None, "Este barbero no tiene usuario de acceso."

    user = db.query(User).filter(User.id == barber.user_id).first()
    if not user:
        return None, "Usuario vinculado no encontrado."

    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()

    state = "activado" if user.is_active else "desactivado"
    create_audit_log(
        db=db,
        module="barberos",
        action="toggle_acceso_barbero",
        detail=f"Admin '{admin_user.username}' {state} el acceso del usuario '{user.username}' (barbero {barber.full_name}).",
        user_id=admin_user.id
    )
    db.commit()

    return {
        "barber_id": barber.id,
        "barber_full_name": barber.full_name,
        "username": user.username,
        "user_is_active": user.is_active
    }, None


def get_barber_user_info(db: Session, barber_id: int):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None, "Barbero no encontrado."

    base = {"barber_id": barber.id, "barber_full_name": barber.full_name}

    if not barber.user_id:
        return {**base, "has_user": False, "username": None, "user_is_active": None}, None

    user = db.query(User).filter(User.id == barber.user_id).first()
    if not user:
        return {**base, "has_user": False, "username": None, "user_is_active": None}, None

    return {**base, "has_user": True, "username": user.username, "user_is_active": user.is_active}, None


def get_barber_performance(db: Session, barber_id: int, start_date=None, end_date=None):
    from datetime import datetime, date, timedelta
    from sqlalchemy import func
    from app.models.order import Order

    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None, "Barbero no encontrado."

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    start_dt = datetime(start_date.year, start_date.month, start_date.day)
    end_dt = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)

    base = (
        db.query(Order)
        .filter(
            Order.barber_id == barber.id,
            Order.status == "cerrada",
            Order.closed_at >= start_dt,
            Order.closed_at < end_dt
        )
    )

    orders_count = base.count()
    sales_total = (
        base.with_entities(func.coalesce(func.sum(Order.total), 0)).scalar()
    )
    sales_total = float(sales_total or 0)

    # Estimación de comisión según el tipo configurado en el barbero.
    commission_type = (barber.commission_type or "").lower()
    commission_value = float(barber.commission_value or 0)
    if commission_type in ("porcentaje", "percent", "%"):
        estimated_commission = sales_total * commission_value / 100.0
    elif commission_type in ("fijo", "fixed", "monto"):
        estimated_commission = commission_value * orders_count
    else:
        estimated_commission = 0.0

    return {
        "barber_id": barber.id,
        "full_name": barber.full_name,
        "alias": barber.alias,
        "period": {"start_date": start_date, "end_date": end_date},
        "orders_count": orders_count,
        "sales_total": sales_total,
        "commission_type": barber.commission_type,
        "commission_value": commission_value,
        "estimated_commission": round(estimated_commission, 2)
    }, None
