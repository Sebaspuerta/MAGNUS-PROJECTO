from datetime import datetime
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.security import User
from app.models.client import Client
from app.models.barber import Barber
from app.models.service import Service
from app.schemas.order import OrderCreate, OrderItemCreate, OrderItemUpdate
from app.services.security_service import create_audit_log


def serialize_order_item(item: OrderItem):
    return {
        "id": item.id,
        "order_id": item.order_id,
        "item_type": item.item_type,
        "service_id": item.service_id,
        "product_id": item.product_id,
        "description": item.description,
        "quantity": item.quantity,
        "unit_price": float(item.unit_price or 0),
        "total_price": float(item.total_price or 0)
    }


def serialize_order(order: Order):
    return {
        "id": order.id,
        "client_id": order.client_id,
        "barber_id": order.barber_id,
        "status": order.status,
        "subtotal": float(order.subtotal or 0),
        "discount": float(order.discount or 0),
        "total": float(order.total or 0),
        "notes": order.notes,
        "created_by_user_id": order.created_by_user_id,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "closed_at": order.closed_at,
        "items": [serialize_order_item(item) for item in order.items]
    }


def _recalculate_order_totals(order: Order):
    order.subtotal = sum(float(item.total_price or 0) for item in order.items)
    order.total = float(order.subtotal or 0) - float(order.discount or 0)
    if order.total < 0:
        order.total = 0


def list_orders(db: Session):
    orders = db.query(Order).order_by(Order.id.asc()).all()
    return [serialize_order(order) for order in orders]


def get_order_by_id(db: Session, order_id: int):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        return None, "Comanda no encontrada."

    return serialize_order(order), None


def create_order(db: Session, payload: OrderCreate, current_user: User):
    if payload.client_id is not None:
        client = db.query(Client).filter(Client.id == payload.client_id).first()
        if not client:
            return None, "Cliente no encontrado."

    if payload.barber_id is not None:
        barber = db.query(Barber).filter(Barber.id == payload.barber_id).first()
        if not barber:
            return None, "Barbero no encontrado."

    order = Order(
        client_id=payload.client_id,
        barber_id=payload.barber_id,
        status="abierta",
        subtotal=0,
        discount=payload.discount,
        total=0,
        notes=payload.notes,
        created_by_user_id=current_user.id
    )

    db.add(order)
    db.flush()

    create_audit_log(
        db=db,
        module="comandas",
        action="crear_comanda",
        detail=f"El usuario {current_user.username} creó la comanda {order.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(order)

    return serialize_order(order), None


def _validate_order_modifiable(order: Order):
    if order.status not in ["abierta", "pendiente"]:
        return False, "La comanda no se puede modificar en su estado actual."
    return True, None


def add_order_item(db: Session, order_id: int, payload: OrderItemCreate, current_user: User):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    valid, error = _validate_order_modifiable(order)
    if not valid:
        return None, error

    if payload.item_type == "servicio":
        if payload.service_id is None:
            return None, "El servicio es obligatorio para ítems de tipo servicio."
        service = db.query(Service).filter(Service.id == payload.service_id, Service.is_active == True).first()
        if not service:
            return None, "Servicio no encontrado o inactivo."
        description = payload.description or service.description or service.name
        unit_price = float(service.price)
        service_id = service.id
        product_id = None
    else:
        description = payload.description
        unit_price = payload.unit_price
        service_id = None
        product_id = payload.product_id

    item = OrderItem(
        order_id=order.id,
        item_type=payload.item_type,
        service_id=service_id,
        product_id=product_id,
        description=description,
        quantity=payload.quantity,
        unit_price=unit_price,
        total_price=float(unit_price) * payload.quantity
    )

    db.add(item)
    db.flush()

    order.items.append(item)
    _recalculate_order_totals(order)
    order.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="comandas",
        action="agregar_item_comanda",
        detail=f"El usuario {current_user.username} agregó un ítem a la comanda {order.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(order)

    return serialize_order(order), None


def update_order_item(db: Session, order_id: int, item_id: int, payload: OrderItemUpdate, current_user: User):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    valid, error = _validate_order_modifiable(order)
    if not valid:
        return None, error

    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order.id).first()
    if not item:
        return None, "Ítem no encontrado en la comanda."

    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.unit_price is not None:
        item.unit_price = payload.unit_price
    if payload.description is not None:
        item.description = payload.description

    item.total_price = float(item.unit_price) * item.quantity
    order.updated_at = datetime.utcnow()
    _recalculate_order_totals(order)

    create_audit_log(
        db=db,
        module="comandas",
        action="editar_item_comanda",
        detail=f"El usuario {current_user.username} actualizó el ítem {item.id} de la comanda {order.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(order)

    return serialize_order(order), None


def delete_order_item(db: Session, order_id: int, item_id: int, current_user: User):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    valid, error = _validate_order_modifiable(order)
    if not valid:
        return None, error

    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order.id).first()
    if not item:
        return None, "Ítem no encontrado en la comanda."

    db.delete(item)
    db.flush()

    _recalculate_order_totals(order)
    order.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="comandas",
        action="eliminar_item_comanda",
        detail=f"El usuario {current_user.username} eliminó el ítem {item.id} de la comanda {order.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(order)

    return serialize_order(order), None


def mark_order_pending(db: Session, order_id: int, current_user: User):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    order.status = "pendiente"
    order.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="comandas",
        action="marcar_comanda_pendiente",
        detail=f"El usuario {current_user.username} marcó la comanda {order.id} como pendiente.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(order)

    return serialize_order(order), None


def cancel_order(db: Session, order_id: int, current_user: User):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    order.status = "cancelada"
    order.updated_at = datetime.utcnow()

    # Aquí se podrá integrar caja, inventario o fiado cuando se implementen esos módulos.
    create_audit_log(
        db=db,
        module="comandas",
        action="cancelar_comanda",
        detail=f"El usuario {current_user.username} canceló la comanda {order.id}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(order)

    return serialize_order(order), None
