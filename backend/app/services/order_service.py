from datetime import datetime
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.security import User
from app.models.client import Client
from app.models.barber import Barber
from app.models.service import Service
from app.models.inventory import InventoryMovement, Product
from app.models.accounts_receivable import AccountsReceivable
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.models.payment import Payment
from app.schemas.order import OrderCreate, OrderItemCreate, OrderItemUpdate, OrderCloseRequest
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
        "payment_status": order.payment_status,
        "amount_paid": float(order.amount_paid or 0),
        "is_fiado": order.is_fiado,
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
        is_fiado=payload.is_fiado,
        payment_status="pendiente",
        amount_paid=0,
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


def _reserve_inventory_for_order(db: Session, order: Order, current_user: User):
    for item in order.items:
        if item.item_type == "producto" and item.product_id:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                return False, "Producto de la comanda no encontrado."
            if product.current_stock < item.quantity:
                return False, f"Stock insuficiente para el producto {product.name}."
            previous_stock = product.current_stock
            product.current_stock -= item.quantity
            movement = InventoryMovement(
                product_id=product.id,
                movement_type="salida_venta",
                quantity=-item.quantity,
                previous_stock=previous_stock,
                new_stock=product.current_stock,
                reason=f"Venta de comanda {order.id}",
                reference_type="order",
                reference_id=order.id,
                created_by_user_id=current_user.id
            )
            db.add(movement)

        elif item.item_type == "servicio" and item.service_id:
            service = db.query(Service).filter(Service.id == item.service_id).first()
            if not service:
                return False, "Servicio de la comanda no encontrado."
            for consumable in service.consumables:
                product = db.query(Product).filter(Product.id == consumable.product_id).first()
                if not product:
                    return False, "Producto consumible no encontrado."
                required_quantity = consumable.quantity * item.quantity
                if product.current_stock < required_quantity:
                    return False, f"Stock insuficiente para el producto {product.name} usado en el servicio {service.name}."
                previous_stock = product.current_stock
                product.current_stock -= required_quantity
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type="salida_servicio",
                    quantity=-required_quantity,
                    previous_stock=previous_stock,
                    new_stock=product.current_stock,
                    reason=f"Consumibles usados en la comanda {order.id}",
                    reference_type="order",
                    reference_id=order.id,
                    created_by_user_id=current_user.id
                )
                db.add(movement)

    return True, None


def _sync_accounts_receivable_for_order(db: Session, order: Order, current_user: User):
    outstanding = float(order.total or 0) - float(order.amount_paid or 0)
    if outstanding <= 0:
        return True, None

    if not order.is_fiado:
        return False, "La comanda debe convertirse a fiado antes de cerrarse con saldo pendiente."

    if not order.client_id:
        return False, "La comanda fiada requiere un cliente asignado."

    accounts_receivable = (
        db.query(AccountsReceivable)
        .filter(AccountsReceivable.order_id == order.id)
        .first()
    )

    if not accounts_receivable:
        accounts_receivable = AccountsReceivable(
            client_id=order.client_id,
            order_id=order.id,
            created_by_user_id=current_user.id,
            total_amount=order.total,
            paid_amount=order.amount_paid,
            balance=outstanding,
            status="pendiente",
            is_active=True
        )
        db.add(accounts_receivable)
    else:
        accounts_receivable.paid_amount = order.amount_paid
        accounts_receivable.balance = outstanding
        accounts_receivable.status = "pagado" if outstanding <= 0 else "pendiente"
        accounts_receivable.updated_at = datetime.utcnow()

    return True, None


def close_order(db: Session, order_id: int, payload: OrderCloseRequest, current_user: User):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "Comanda no encontrada."

    if order.status in ["cancelada", "cerrada"]:
        return None, "La comanda no se puede cerrar en su estado actual."

    if not order.items:
        return None, "La comanda no tiene ítems. Agregue al menos un ítem antes de cerrar."

    try:
        # 1) Barbero obligatorio
        if payload.barber_id:
            barber = db.query(Barber).filter(
                Barber.id == payload.barber_id,
                Barber.is_active == True
            ).first()
            if not barber:
                db.rollback()
                return None, "El barbero indicado no existe o está inactivo."
            order.barber_id = payload.barber_id

        if not order.barber_id:
            db.rollback()
            return None, "Debe asignar un barbero responsable antes de cerrar la comanda."

        # 2) Descuento de inventario
        valid, error = _reserve_inventory_for_order(db, order, current_user)
        if not valid:
            db.rollback()
            return None, error

        # 3) Pago si no es fiado y hay saldo pendiente
        outstanding = float(order.total or 0) - float(order.amount_paid or 0)
        if not order.is_fiado and outstanding > 0:
            if not payload.payment_method:
                db.rollback()
                return None, "Debe indicar el método de pago."

            amount = payload.payment_amount if payload.payment_amount is not None else outstanding
            if amount <= 0:
                db.rollback()
                return None, "El monto de pago debe ser mayor que cero."
            if amount > outstanding + 0.01:
                db.rollback()
                return None, f"El monto ingresado supera el saldo pendiente de ${outstanding:,.0f} COP."

            # Buscar caja abierta
            if payload.cash_register_id:
                cash_register = db.query(CashRegister).filter(
                    CashRegister.id == payload.cash_register_id,
                    CashRegister.is_closed == False
                ).first()
                if not cash_register:
                    db.rollback()
                    return None, "La caja indicada no existe o está cerrada."
            else:
                open_registers = db.query(CashRegister).filter(
                    CashRegister.is_closed == False
                ).all()
                if not open_registers:
                    db.rollback()
                    return None, "No hay una caja abierta. Abra la caja antes de cobrar."
                if len(open_registers) > 1:
                    db.rollback()
                    return None, "Hay múltiples cajas abiertas. Indique cuál utilizar en el campo cash_register_id."
                cash_register = open_registers[0]

            payment = Payment(
                order_id=order.id,
                user_id=current_user.id,
                cash_register_id=cash_register.id,
                payment_method=payload.payment_method,
                amount=amount,
                note=payload.note
            )
            db.add(payment)
            db.flush()

            movement = CashMovement(
                cash_register_id=cash_register.id,
                user_id=current_user.id,
                movement_type="ingreso_venta",
                amount=amount,
                payment_method=payload.payment_method,
                description=f"Pago de comanda {order.id}",
                reference_type="order",
                reference_id=order.id
            )
            db.add(movement)
            db.flush()

            order.amount_paid = float(order.amount_paid or 0) + amount

        # 4) Estado de la comanda
        order.status = "cerrada"
        order.closed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        paid = float(order.amount_paid or 0)
        total = float(order.total or 0)
        if order.is_fiado:
            order.payment_status = "fiado"
        elif paid >= total:
            order.payment_status = "pagado"
        else:
            order.payment_status = "parcial"

        # 5) Cuentas por cobrar si es fiado con saldo
        if order.is_fiado:
            valid, error = _sync_accounts_receivable_for_order(db, order, current_user)
            if not valid:
                db.rollback()
                return None, error

        # 6) Auditoría y commit único
        create_audit_log(
            db=db,
            module="comandas",
            action="cerrar_comanda",
            detail=f"El usuario {current_user.username} cerró la comanda {order.id}. Estado de pago: {order.payment_status}.",
            user_id=current_user.id
        )

        db.commit()
        db.refresh(order)
        return serialize_order(order), None

    except Exception as e:
        db.rollback()
        return None, f"Error al cerrar la comanda: {str(e)}"


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
