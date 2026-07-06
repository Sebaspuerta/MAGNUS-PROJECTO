from datetime import datetime
from sqlalchemy.orm import Session

from app.models.inventory import InventoryMovement, Product
from app.models.security import User
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryEntryCreate,
    ProductCreate,
    ProductUpdate
)
from app.services.security_service import create_audit_log


VALID_PRODUCT_TYPES = ["venta", "consumible_interno", "perecedero"]


def serialize_product(product: Product):
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "product_type": product.product_type,
        "description": product.description,
        "purchase_cost": float(product.purchase_cost or 0),
        "sale_price": float(product.sale_price or 0),
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "expiration_date": product.expiration_date,
        "supplier": product.supplier,
        "is_active": product.is_active
    }


def serialize_inventory_movement(movement: InventoryMovement):
    return {
        "id": movement.id,
        "product_id": movement.product_id,
        "movement_type": movement.movement_type,
        "quantity": movement.quantity,
        "previous_stock": movement.previous_stock,
        "new_stock": movement.new_stock,
        "reason": movement.reason,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "created_by_user_id": movement.created_by_user_id,
        "created_at": movement.created_at
    }


def list_products(db: Session, include_inactive: bool = False):
    query = db.query(Product).order_by(Product.id.asc())

    if not include_inactive:
        query = query.filter(Product.is_active == True)

    return [serialize_product(product) for product in query.all()]


def get_product_by_id(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return None, "Producto no encontrado."

    return serialize_product(product), None


def create_product(db: Session, payload: ProductCreate, admin_user: User):
    if payload.product_type not in VALID_PRODUCT_TYPES:
        return None, "Tipo de producto inválido."

    product = Product(
        name=payload.name,
        category=payload.category,
        product_type=payload.product_type,
        description=payload.description,
        purchase_cost=payload.purchase_cost,
        sale_price=payload.sale_price,
        current_stock=payload.current_stock,
        minimum_stock=payload.minimum_stock,
        expiration_date=payload.expiration_date,
        supplier=payload.supplier,
        is_active=True
    )

    db.add(product)
    db.flush()

    create_audit_log(
        db=db,
        module="inventario",
        action="crear_producto",
        detail=f"El administrador {admin_user.username} creó el producto {product.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(product)

    return serialize_product(product), None


def update_product(db: Session, product_id: int, payload: ProductUpdate, admin_user: User):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return None, "Producto no encontrado."

    if payload.product_type is not None:
        if payload.product_type not in VALID_PRODUCT_TYPES:
            return None, "Tipo de producto inválido."
        product.product_type = payload.product_type

    if payload.name is not None:
        product.name = payload.name
    if payload.category is not None:
        product.category = payload.category
    if payload.description is not None:
        product.description = payload.description
    if payload.purchase_cost is not None:
        product.purchase_cost = payload.purchase_cost
    if payload.sale_price is not None:
        product.sale_price = payload.sale_price
    if payload.current_stock is not None:
        if payload.current_stock < 0:
            return None, "El stock no puede ser negativo."
        product.current_stock = payload.current_stock
    if payload.minimum_stock is not None:
        product.minimum_stock = payload.minimum_stock
    if payload.expiration_date is not None:
        product.expiration_date = payload.expiration_date
    if payload.supplier is not None:
        product.supplier = payload.supplier
    if payload.is_active is not None:
        product.is_active = payload.is_active

    product.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="inventario",
        action="editar_producto",
        detail=f"El administrador {admin_user.username} editó el producto {product.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(product)

    return serialize_product(product), None


def delete_product(db: Session, product_id: int, admin_user: User):
    from app.models.order import OrderItem
    from app.models.service_consumable import ServiceConsumable

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None, "Producto no encontrado."

    has_orders = (
        db.query(OrderItem).filter(OrderItem.product_id == product_id).first()
    )
    if has_orders:
        return None, {
            "code": "has_history",
            "message": (
                f"El producto '{product.name}' ya tiene ventas registradas en comandas. "
                "Para retirarlo del catálogo, desactívalo en lugar de eliminarlo "
                "(así el historial de ventas queda intacto)."
            )
        }

    has_movements = (
        db.query(InventoryMovement).filter(InventoryMovement.product_id == product_id).first()
    )
    if has_movements:
        return None, {
            "code": "has_history",
            "message": (
                f"El producto '{product.name}' tiene movimientos de inventario registrados. "
                "Para retirarlo del catálogo, desactívalo en lugar de eliminarlo."
            )
        }

    has_consumables = (
        db.query(ServiceConsumable).filter(ServiceConsumable.product_id == product_id).first()
    )
    if has_consumables:
        return None, {
            "code": "has_history",
            "message": (
                f"El producto '{product.name}' está configurado como consumible de uno o más "
                "servicios. Retíralo de esa configuración antes de eliminarlo."
            )
        }

    name = product.name
    db.delete(product)

    create_audit_log(
        db=db,
        module="inventario",
        action="eliminar_producto",
        detail=f"El administrador '{admin_user.username}' eliminó el producto '{name}' (ID: {product_id}).",
        user_id=admin_user.id
    )

    db.commit()
    return {"detail": f"Producto '{name}' eliminado correctamente."}, None


def deactivate_product(db: Session, product_id: int, admin_user: User):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return None, "Producto no encontrado."

    product.is_active = False
    product.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="inventario",
        action="desactivar_producto",
        detail=f"El administrador {admin_user.username} desactivó el producto {product.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(product)

    return serialize_product(product), None


def create_inventory_entry(db: Session, product_id: int, payload: InventoryEntryCreate, admin_user: User):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None, "Producto no encontrado."

    previous_stock = product.current_stock
    new_stock = previous_stock + payload.quantity

    movement = InventoryMovement(
        product_id=product.id,
        movement_type="entrada",
        quantity=payload.quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=payload.reason,
        created_by_user_id=admin_user.id
    )

    product.current_stock = new_stock
    product.updated_at = datetime.utcnow()

    db.add(movement)
    db.flush()

    create_audit_log(
        db=db,
        module="inventario",
        action="entrada_inventario",
        detail=f"El administrador {admin_user.username} registró entrada de inventario para el producto {product.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(product)

    return serialize_product(product), None


def create_inventory_adjustment(db: Session, product_id: int, payload: InventoryAdjustmentCreate, admin_user: User):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None, "Producto no encontrado."

    previous_stock = product.current_stock
    new_stock = previous_stock + payload.quantity

    if new_stock < 0:
        return None, "El stock no puede quedar en valor negativo."

    movement = InventoryMovement(
        product_id=product.id,
        movement_type="ajuste",
        quantity=payload.quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=payload.reason,
        created_by_user_id=admin_user.id
    )

    product.current_stock = new_stock
    product.updated_at = datetime.utcnow()

    db.add(movement)
    db.flush()

    create_audit_log(
        db=db,
        module="inventario",
        action="ajuste_inventario",
        detail=f"El administrador {admin_user.username} registró ajuste de inventario para el producto {product.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(product)

    return serialize_product(product), None


def list_product_movements(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None, "Producto no encontrado."

    movements = (
        db.query(InventoryMovement)
        .filter(InventoryMovement.product_id == product.id)
        .order_by(InventoryMovement.created_at.asc())
        .all()
    )

    return [serialize_inventory_movement(movement) for movement in movements], None
