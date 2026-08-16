import io
from datetime import datetime
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import InventoryMovement, Product
from app.models.security import User
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryEntryCreate,
    ProductCreate,
    ProductUpdate
)
from app.services.security_service import create_audit_log
from app.utils.deleted_labels import category_label


VALID_PRODUCT_TYPES = ["venta", "consumible_interno", "perecedero"]

# backend/app/services/inventory_service.py -> parents[2] == backend/
PRODUCT_PHOTOS_DIR = Path(__file__).resolve().parents[2] / "static" / "product_photos"
ALLOWED_PHOTO_FORMATS = {"PNG", "JPEG", "WEBP"}
PHOTO_THUMBNAIL_SIZE = 200


def _build_photo_url(photo_filename: str | None) -> str | None:
    if not photo_filename:
        return None
    return f"/media/{photo_filename}"


def serialize_product(product: Product):
    category = product.category_ref
    return {
        "id": product.id,
        "name": product.name,
        "category_id": product.category_id,
        "category_name": category_label(category.name, category) if category else None,
        "category_is_deleted": bool(category and category.is_deleted),
        "product_type": product.product_type,
        "description": product.description,
        "purchase_cost": float(product.purchase_cost or 0),
        "sale_price": float(product.sale_price or 0),
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "expiration_date": product.expiration_date,
        "supplier": product.supplier,
        "is_active": product.is_active,
        "is_deleted": product.is_deleted,
        "photo_filename": product.photo_filename,
        "photo_url": _build_photo_url(product.photo_filename)
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


def get_live_product(db: Session, product_id: int) -> Product | None:
    """Producto no eliminado. Los eliminados (is_deleted) nunca se devuelven:
    quedan solo en el historial ya registrado, no se pueden volver a usar ni
    editar, sin importar include_inactive."""
    return (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_deleted == False)  # noqa: E712
        .first()
    )


def list_products(db: Session, include_inactive: bool = False, category_id: int | None = None):
    query = (
        db.query(Product)
        .filter(Product.is_deleted == False)  # noqa: E712
        .order_by(Product.id.asc())
    )

    if not include_inactive:
        query = query.filter(Product.is_active == True)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    return [serialize_product(product) for product in query.all()]


def get_product_by_id(db: Session, product_id: int):
    product = get_live_product(db, product_id)

    if not product:
        return None, "Producto no encontrado."

    return serialize_product(product), None


def _validate_category_id(db: Session, category_id: int | None):
    if category_id is None:
        return None
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.is_deleted == False)  # noqa: E712
        .first()
    )
    if not category:
        return "Categoría no encontrada."
    return None


def create_product(db: Session, payload: ProductCreate, admin_user: User):
    if payload.product_type not in VALID_PRODUCT_TYPES:
        return None, "Tipo de producto inválido."

    error = _validate_category_id(db, payload.category_id)
    if error:
        return None, error

    product = Product(
        name=payload.name,
        category_id=payload.category_id,
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
    product = get_live_product(db, product_id)

    if not product:
        return None, "Producto no encontrado."

    if payload.product_type is not None:
        if payload.product_type not in VALID_PRODUCT_TYPES:
            return None, "Tipo de producto inválido."
        product.product_type = payload.product_type

    if payload.name is not None:
        product.name = payload.name
    if payload.category_id is not None:
        error = _validate_category_id(db, payload.category_id)
        if error:
            return None, error
        product.category_id = payload.category_id
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
    """Borrado lógico: nunca se hace db.delete(). El producto se marca como
    eliminado y deja de estar disponible para cualquier uso futuro, pero las
    ventas y movimientos de inventario ya registrados quedan intactos."""
    product = get_live_product(db, product_id)
    if not product:
        return None, "Producto no encontrado."

    name = product.name
    product.is_deleted = True
    product.is_active = False
    product.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="inventario",
        action="eliminar_producto",
        detail=f"El dueño '{admin_user.username}' eliminó el producto '{name}' (ID: {product_id}).",
        user_id=admin_user.id
    )

    db.commit()
    return {"detail": f"Producto '{name}' eliminado correctamente."}, None


def deactivate_product(db: Session, product_id: int, admin_user: User):
    product = get_live_product(db, product_id)

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
    product = get_live_product(db, product_id)
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
    product = get_live_product(db, product_id)
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


def _crop_to_square_thumbnail(image: Image.Image, size: int) -> Image.Image:
    """Recorta al centro al lado más corto (sin deformar) y redimensiona al
    cuadrado fijo solicitado."""
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    cropped = image.crop((left, top, left + side, top + side))
    return cropped.resize((size, size), Image.LANCZOS)


def save_product_photo(db: Session, product_id: int, file_bytes: bytes, admin_user: User):
    """Valida, recorta a cuadrado y guarda como PNG 200x200 la foto de un
    producto. El formato real se determina con Pillow (no se confía en el
    Content-Type ni en la extensión que envía el cliente)."""
    product = get_live_product(db, product_id)
    if not product:
        return None, "Producto no encontrado."

    if not file_bytes:
        return None, "El archivo de imagen está vacío."

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except (UnidentifiedImageError, OSError):
        return None, "El archivo no es una imagen válida."

    if image.format not in ALLOWED_PHOTO_FORMATS:
        return None, "Formato no soportado. Usa PNG, JPG/JPEG o WEBP."

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    thumbnail = _crop_to_square_thumbnail(image, PHOTO_THUMBNAIL_SIZE)

    PRODUCT_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    destination = PRODUCT_PHOTOS_DIR / f"{product.id}.png"
    thumbnail.save(destination, format="PNG")

    product.photo_filename = f"product_photos/{product.id}.png"
    product.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="inventario",
        action="subir_foto_producto",
        detail=f"El administrador {admin_user.username} actualizó la foto del producto {product.name}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(product)

    return serialize_product(product), None


def list_product_movements(db: Session, product_id: int):
    product = get_live_product(db, product_id)
    if not product:
        return None, "Producto no encontrado."

    movements = (
        db.query(InventoryMovement)
        .filter(InventoryMovement.product_id == product.id)
        .order_by(InventoryMovement.created_at.asc())
        .all()
    )

    return [serialize_inventory_movement(movement) for movement in movements], None
