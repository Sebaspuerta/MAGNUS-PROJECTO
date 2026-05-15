from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.service_consumable import (
    ServiceConsumableCreate,
    ServiceConsumableResponse,
    ServiceConsumableUpdate
)
from app.services.service_consumable_service import (
    create_service_consumable,
    delete_service_consumable,
    list_service_consumables,
    update_service_consumable
)
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/service-consumables",
    tags=["Consumibles de Servicio"]
)


@router.get("", response_model=list[ServiceConsumableResponse])
def get_service_consumables(
    service_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("servicios.ver"))
):
    return list_service_consumables(db, service_id=service_id)


@router.post("", response_model=ServiceConsumableResponse)
def post_service_consumable(
    payload: ServiceConsumableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("servicios.editar"))
):
    result, error = create_service_consumable(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.patch("/{consumable_id}", response_model=ServiceConsumableResponse)
def patch_service_consumable(
    consumable_id: int,
    payload: ServiceConsumableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("servicios.editar"))
):
    result, error = update_service_consumable(db, consumable_id, payload, current_user)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result


@router.delete("/{consumable_id}")
def delete_service_consumable_route(
    consumable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("servicios.editar"))
):
    result, error = delete_service_consumable(db, consumable_id, current_user)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result
