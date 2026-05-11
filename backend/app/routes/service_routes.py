from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from app.services.service_service import (
    create_service,
    deactivate_service,
    get_service_by_id,
    list_services,
    update_service
)
from app.utils.security import get_current_user, require_admin


router = APIRouter(
    prefix="/api/services",
    tags=["Catálogo de Servicios"]
)


@router.get("", response_model=list[ServiceResponse])
def get_services(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return list_services(db, include_inactive=include_inactive)


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result, error = get_service_by_id(db, service_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.post("", response_model=ServiceResponse)
def post_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = create_service(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{service_id}", response_model=ServiceResponse)
def patch_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = update_service(db, service_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{service_id}/deactivate", response_model=ServiceResponse)
def patch_deactivate_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = deactivate_service(db, service_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result
