from datetime import datetime
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.security import User
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.services.security_service import create_audit_log


def serialize_service(service: Service):
    return {
        "id": service.id,
        "name": service.name,
        "category": service.category,
        "description": service.description,
        "price": float(service.price or 0),
        "estimated_duration_minutes": service.estimated_duration_minutes,
        "uses_internal_consumables": service.uses_internal_consumables,
        "is_active": service.is_active
    }


def list_services(db: Session, include_inactive: bool = False):
    query = db.query(Service).order_by(Service.id.asc())

    if not include_inactive:
        query = query.filter(Service.is_active == True)

    return [serialize_service(service) for service in query.all()]


def get_service_by_id(db: Session, service_id: int):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        return None, "Servicio no encontrado."

    return serialize_service(service), None


def create_service(db: Session, payload: ServiceCreate, admin_user: User):
    existing_service = (
        db.query(Service)
        .filter(Service.name == payload.name, Service.is_active == True)
        .first()
    )

    if existing_service:
        return None, "Ya existe un servicio activo con ese nombre."

    service = Service(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        price=payload.price,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        uses_internal_consumables=payload.uses_internal_consumables,
        is_active=True
    )

    db.add(service)
    db.flush()

    create_audit_log(
        db=db,
        module="servicios",
        action="crear_servicio",
        detail=f"El administrador {admin_user.username} creó el servicio {service.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(service)

    return serialize_service(service), None


def update_service(db: Session, service_id: int, payload: ServiceUpdate, admin_user: User):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        return None, "Servicio no encontrado."

    if payload.name is not None:
        existing_service = (
            db.query(Service)
            .filter(Service.name == payload.name, Service.id != service.id, Service.is_active == True)
            .first()
        )
        if existing_service:
            return None, "Ya existe un servicio activo con ese nombre."
        service.name = payload.name

    if payload.category is not None:
        service.category = payload.category

    if payload.description is not None:
        service.description = payload.description

    if payload.price is not None:
        service.price = payload.price

    if payload.estimated_duration_minutes is not None:
        service.estimated_duration_minutes = payload.estimated_duration_minutes

    if payload.uses_internal_consumables is not None:
        service.uses_internal_consumables = payload.uses_internal_consumables

    if payload.is_active is not None:
        service.is_active = payload.is_active

    service.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="servicios",
        action="editar_servicio",
        detail=f"El administrador {admin_user.username} editó el servicio {service.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(service)

    return serialize_service(service), None


def delete_service(db: Session, service_id: int, admin_user: User):
    from app.models.order import OrderItem

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return None, "Servicio no encontrado."

    has_orders = db.query(OrderItem).filter(OrderItem.service_id == service_id).first()
    if has_orders:
        return None, {
            "code": "has_history",
            "message": (
                f"El servicio '{service.name}' ya tiene ventas registradas en comandas. "
                "Para dejar de ofrecerlo, desactívalo en lugar de eliminarlo "
                "(así el historial queda intacto)."
            )
        }

    name = service.name
    db.delete(service)

    create_audit_log(
        db=db,
        module="servicios",
        action="eliminar_servicio",
        detail=f"El administrador '{admin_user.username}' eliminó el servicio '{name}' (ID: {service_id}).",
        user_id=admin_user.id
    )

    db.commit()
    return {"detail": f"Servicio '{name}' eliminado correctamente."}, None


def deactivate_service(db: Session, service_id: int, admin_user: User):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        return None, "Servicio no encontrado."

    service.is_active = False
    service.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="servicios",
        action="desactivar_servicio",
        detail=f"El administrador {admin_user.username} desactivó el servicio {service.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(service)

    return serialize_service(service), None
