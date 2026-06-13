from datetime import datetime
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.security import User
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.security_service import create_audit_log


def serialize_client(client: Client):
    return {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "email": client.email,
        "document_number": client.document_number,
        "birth_date": client.birth_date,
        "notes": client.notes,
        "is_active": client.is_active
    }


def list_clients(db: Session, include_inactive: bool = False):
    query = db.query(Client).order_by(Client.id.asc())

    if not include_inactive:
        query = query.filter(Client.is_active == True)

    return [serialize_client(client) for client in query.all()]


def get_client_by_id(db: Session, client_id: int):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        return None, "Cliente no encontrado."

    return serialize_client(client), None


def create_client(db: Session, payload: ClientCreate, admin_user: User):
    client = Client(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        document_number=payload.document_number,
        birth_date=payload.birth_date,
        notes=payload.notes,
        is_active=True
    )

    db.add(client)
    db.flush()

    create_audit_log(
        db=db,
        module="clientes",
        action="crear_cliente",
        detail=f"El administrador {admin_user.username} creó el cliente {client.full_name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(client)

    return serialize_client(client), None


def update_client(db: Session, client_id: int, payload: ClientUpdate, admin_user: User):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        return None, "Cliente no encontrado."

    if payload.full_name is not None:
        client.full_name = payload.full_name

    if payload.phone is not None:
        client.phone = payload.phone

    if payload.email is not None:
        client.email = payload.email

    if payload.document_number is not None:
        client.document_number = payload.document_number

    if payload.birth_date is not None:
        client.birth_date = payload.birth_date

    if payload.notes is not None:
        client.notes = payload.notes

    if payload.is_active is not None:
        client.is_active = payload.is_active

    client.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="clientes",
        action="editar_cliente",
        detail=f"El administrador {admin_user.username} editó el cliente {client.full_name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(client)

    return serialize_client(client), None


def deactivate_client(db: Session, client_id: int, admin_user: User):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        return None, "Cliente no encontrado."

    client.is_active = False
    client.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="clientes",
        action="desactivar_cliente",
        detail=f"El administrador {admin_user.username} desactivó el cliente {client.full_name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(client)

    return serialize_client(client), None


def get_client_profile(db: Session, client_id: int):
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.order import Order
    from app.models.accounts_receivable import AccountsReceivable

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return None, "Cliente no encontrado."

    closed = (
        db.query(Order)
        .filter(Order.client_id == client.id, Order.status == "cerrada")
    )
    visits_count = closed.count()
    total_spent = float(
        closed.with_entities(func.coalesce(func.sum(Order.total), 0)).scalar() or 0
    )
    last_order = (
        closed.order_by(Order.closed_at.desc()).first()
    )
    last_visit = last_order.closed_at if last_order else None

    outstanding = float(
        db.query(func.coalesce(func.sum(AccountsReceivable.balance), 0))
        .filter(
            AccountsReceivable.client_id == client.id,
            AccountsReceivable.is_active == True,  # noqa: E712
            AccountsReceivable.balance > 0
        )
        .scalar() or 0
    )

    # Estado derivado (sin columnas nuevas): se calcula a partir del historial.
    if outstanding > 0:
        state = "Deudor"
    elif visits_count == 0:
        state = "Nuevo"
    elif total_spent >= 200000 or visits_count >= 10:
        state = "VIP"
    elif visits_count >= 3:
        state = "Frecuente"
    else:
        state = "Nuevo"

    if last_visit and last_visit < datetime.utcnow() - timedelta(days=90):
        state = "Inactivo" if outstanding <= 0 else state

    profile = serialize_client(client)
    profile.update({
        "state": state,
        "visits_count": visits_count,
        "total_spent": round(total_spent, 2),
        "last_visit": last_visit,
        "outstanding_balance": round(outstanding, 2),
        "has_debt": outstanding > 0
    })
    return profile, None
