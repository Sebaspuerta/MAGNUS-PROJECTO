from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import Product
from app.models.security import User
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
    return [serialize_category(db, category) for category in categories]


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
    db.flush()

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


def delete_category(db: Session, category_id: int, admin_user: User):
    """Borrado lógico: nunca db.delete(). Rechaza si quedan productos activos
    (is_deleted=False AND is_active=True) apuntando a esta categoría."""
    category = get_live_category(db, category_id)
    if not category:
        return None, "Categoría no encontrada."

    active_count = _active_product_count(db, category.id)
    if active_count > 0:
        noun = "producto activo" if active_count == 1 else "productos activos"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Esta categoría tiene {active_count} {noun}. "
                "Elimínalos primero para poder borrar la categoría."
            )
        )

    name = category.name
    category.is_deleted = True
    category.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="inventario",
        action="eliminar_categoria",
        detail=f"El dueño '{admin_user.username}' eliminó la categoría '{name}' (ID: {category_id}).",
        user_id=admin_user.id
    )

    db.commit()
    return {"detail": f"Categoría '{name}' eliminada correctamente."}, None