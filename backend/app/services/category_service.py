from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import Product
from app.models.security import User
from app.services.inventory_service import delete_product
from app.services.security_service import create_audit_log


def get_live_category(db: Session, category_id: int) -> Category | None:
    """Categoría no eliminada. Las eliminadas (is_deleted) nunca se devuelven:
    no se pueden volver a usar en nada nuevo."""
    return (
        db.query(Category)
        .filter(Category.id == category_id, Category.is_deleted == False)  # noqa: E712
        .first()
    )


def _active_product_count(db: Session, category_id: int) -> int:
    return (
        db.query(func.count(Product.id))
        .filter(
            Product.category_id == category_id,
            Product.is_deleted == False,  # noqa: E712
            Product.is_active == True  # noqa: E712
        )
        .scalar()
    ) or 0


def uncategorized_active_count(db: Session) -> int:
    return (
        db.query(func.count(Product.id))
        .filter(
            Product.category_id.is_(None),
            Product.is_deleted == False,  # noqa: E712
            Product.is_active == True  # noqa: E712
        )
        .scalar()
    ) or 0


def serialize_category(db: Session, category: Category):
    return {
        "id": category.id,
        "name": category.name,
        "is_deleted": category.is_deleted,
        "product_count": _active_product_count(db, category.id)
    }


def list_categories(db: Session):
    categories = (
        db.query(Category)
        .filter(Category.is_deleted == False)  # noqa: E712
        .order_by(Category.name.asc())
        .all()
    )
    result = [serialize_category(db, category) for category in categories]

    # Tarjeta virtual "Sin categoría": solo aparece si hay al menos un producto
    # activo sin categoría asignada (p. ej. tras eliminar la categoría que tenían).
    uncategorized_count = uncategorized_active_count(db)
    if uncategorized_count > 0:
        result.append({
            "id": None,
            "name": "Sin categoría",
            "is_deleted": False,
            "product_count": uncategorized_count
        })

    return result


def create_category(db: Session, name: str, admin_user: User):
    clean_name = (name or "").strip()
    if not clean_name:
        return None, "El nombre de la categoría es obligatorio."

    existing = (
        db.query(Category)
        .filter(
            func.lower(Category.name) == clean_name.lower(),
            Category.is_deleted == False  # noqa: E712
        )
        .first()
    )
    if existing:
        return None, "Ya existe una categoría activa con ese nombre."

    category = Category(name=clean_name, is_deleted=False)
    db.add(category)
    try:
        db.flush()
    except IntegrityError:
        # Red de seguridad además del chequeo de arriba (p. ej. condición de
        # carrera entre dos solicitudes simultáneas) — nunca debe llegar un
        # 500 crudo al usuario por un nombre duplicado.
        db.rollback()
        return None, "Ya existe una categoría activa con ese nombre."

    create_audit_log(
        db=db,
        module="inventario",
        action="crear_categoria",
        detail=f"El dueño {admin_user.username} creó la categoría '{category.name}'.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(category)

    return serialize_category(db, category), None


def delete_category(db: Session, category_id: int, admin_user: User, delete_products: bool = False):
    """Borrado lógico: nunca db.delete(). No se bloquea por tener productos
    adentro. Dos modos, a elección de quien elimina:
    - delete_products=False (default): sus productos pasan automáticamente a
      "sin categoría" (category_id=None); ningún dato se toca ni se pierde.
    - delete_products=True: además se eliminan lógicamente todos sus productos,
      reutilizando exactamente el mismo borrado lógico de delete_product
      (is_deleted=True, is_active=False) — nunca db.delete(), el historial de
      ventas y movimientos ya registrado queda intacto."""
    category = get_live_category(db, category_id)
    if not category:
        return None, "Categoría no encontrada."

    if delete_products:
        productos = (
            db.query(Product)
            .filter(Product.category_id == category_id, Product.is_deleted == False)  # noqa: E712
            .all()
        )
        for producto in productos:
            delete_product(db, producto.id, admin_user)
        detail_extra = f"{len(productos)} producto(s) fueron eliminados junto con la categoría."
    else:
        moved = (
            db.query(Product)
            .filter(Product.category_id == category_id)
            .update({"category_id": None}, synchronize_session=False)
        )
        detail_extra = f"{moved} producto(s) pasaron a 'Sin categoría'."

    name = category.name
    category.is_deleted = True
    category.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="inventario",
        action="eliminar_categoria",
        detail=(
            f"El dueño '{admin_user.username}' eliminó la categoría '{name}' "
            f"(ID: {category_id}). {detail_extra}"
        ),
        user_id=admin_user.id
    )

    db.commit()
    return {"detail": f"Categoría '{name}' eliminada. {detail_extra}"}, None