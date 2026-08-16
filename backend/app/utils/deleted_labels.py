"""Etiquetas para nombres de entidades marcadas como eliminadas (is_deleted).

El historial (comandas, reportes, Excel) sigue mostrando el nombre original que
quedó registrado en la venta; estas funciones solo le agregan el sufijo cuando
el producto/servicio/barbero relacionado fue eliminado del sistema.
"""

DELETED_PRODUCT_SUFFIX = " (producto eliminado del sistema)"
DELETED_SERVICE_SUFFIX = " (servicio eliminado del sistema)"
DELETED_BARBER_SUFFIX = " (barbero eliminado del sistema)"
DELETED_CATEGORY_SUFFIX = " (categoría eliminada del sistema)"


def _is_deleted(entity) -> bool:
    return bool(entity is not None and getattr(entity, "is_deleted", False))


def _label(name: str | None, entity, suffix: str) -> str | None:
    if name is None:
        return None
    if not _is_deleted(entity):
        return name
    if name.endswith(suffix):
        return name
    return f"{name}{suffix}"


def product_label(name: str | None, product) -> str | None:
    """Nombre a mostrar para un producto (o el nombre guardado en la venta)."""
    return _label(name, product, DELETED_PRODUCT_SUFFIX)


def service_label(name: str | None, service) -> str | None:
    """Nombre a mostrar para un servicio (o el nombre guardado en la venta)."""
    return _label(name, service, DELETED_SERVICE_SUFFIX)


def barber_label(name: str | None, barber) -> str | None:
    """Nombre a mostrar para un barbero."""
    return _label(name, barber, DELETED_BARBER_SUFFIX)


def category_label(name: str | None, category) -> str | None:
    """Nombre a mostrar para la categoría de un producto."""
    return _label(name, category, DELETED_CATEGORY_SUFFIX)
