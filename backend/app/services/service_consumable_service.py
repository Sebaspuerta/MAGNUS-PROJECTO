from datetime import datetime
from sqlalchemy.orm import Session

from app.models.service_consumable import ServiceConsumable
from app.models.service import Service
from app.models.inventory import Product
from app.models.security import User
from app.schemas.service_consumable import ServiceConsumableCreate, ServiceConsumableUpdate
from app.services.security_service import create_audit_log


def serialize_service_consumable(consumable: ServiceConsumable):
    return {
        "id": consumable.id,
        "service_id": consumable.service_id,
        "product_id": consumable.product_id,
        "quantity": consumable.quantity,
        "created_at": consumable.created_at
    }


def list_service_consumables(db: Session, service_id: int | None = None):
    query = db.query(ServiceConsumable).order_by(ServiceConsumable.id.asc())
    if service_id is not None:
        query = query.filter(ServiceConsumable.service_id == service_id)
    return [serialize_service_consumable(consumable) for consumable in query.all()]


def create_service_consumable(db: Session, payload: ServiceConsumableCreate, current_user: User):
    service = db.query(Service).filter(Service.id == payload.service_id, Service.is_active == True).first()
    if not service:
        return None, "Servicio no encontrado o inactivo."

    product = db.query(Product).filter(Product.id == payload.product_id, Product.is_active == True).first()
    if not product:
        return None, "Producto no encontrado o inactivo."

    existing = (
        db.query(ServiceConsumable)
        .filter(
            ServiceConsumable.service_id == payload.service_id,
            ServiceConsumable.product_id == payload.product_id
        )
        .first()
    )
    if existing:
        return None, "Ya existe un insumo para ese servicio y producto."

    consumable = ServiceConsumable(
        service_id=payload.service_id,
        product_id=payload.product_id,
        quantity=payload.quantity
    )
    db.add(consumable)
    db.flush()

    create_audit_log(
        db=db,
        module="servicios",
        action="crear_consumible",
        detail=f"El usuario {current_user.username} agregó un consumible al servicio {service.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(consumable)
    return serialize_service_consumable(consumable), None


def update_service_consumable(db: Session, consumable_id: int, payload: ServiceConsumableUpdate, current_user: User):
    consumable = db.query(ServiceConsumable).filter(ServiceConsumable.id == consumable_id).first()
    if not consumable:
        return None, "Consumible no encontrado."

    if payload.quantity is not None:
        consumable.quantity = payload.quantity

    create_audit_log(
        db=db,
        module="servicios",
        action="editar_consumible",
        detail=f"El usuario {current_user.username} actualizó el consumible {consumable.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(consumable)
    return serialize_service_consumable(consumable), None


def delete_service_consumable(db: Session, consumable_id: int, current_user: User):
    consumable = db.query(ServiceConsumable).filter(ServiceConsumable.id == consumable_id).first()
    if not consumable:
        return None, "Consumible no encontrado."

    db.delete(consumable)

    create_audit_log(
        db=db,
        module="servicios",
        action="eliminar_consumible",
        detail=f"El usuario {current_user.username} eliminó el consumible {consumable.id}.",
        user_id=current_user.id
    )

    db.commit()
    return {"message": "Consumible eliminado correctamente."}, None
