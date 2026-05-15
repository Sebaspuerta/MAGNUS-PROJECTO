from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.barber import BarberCreate, BarberResponse, BarberUpdate
from app.services.barber_service import (
    create_barber,
    deactivate_barber,
    get_barber_by_id,
    list_barbers,
    update_barber
)
from app.utils.security import get_current_user, require_permission


router = APIRouter(
    prefix="/api/barbers",
    tags=["Gestión de Barberos"]
)


@router.get("", response_model=list[BarberResponse])
def get_barbers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("barberos.ver"))
):
    return list_barbers(db, include_inactive=include_inactive)


@router.get("/{barber_id}", response_model=BarberResponse)
def get_barber(
    barber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("barberos.ver"))
):
    result, error = get_barber_by_id(db, barber_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.post("", response_model=BarberResponse)
def post_barber(
    payload: BarberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("barberos.crear"))
):
    result, error = create_barber(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{barber_id}", response_model=BarberResponse)
def patch_barber(
    barber_id: int,
    payload: BarberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("barberos.editar"))
):
    result, error = update_barber(db, barber_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{barber_id}/deactivate", response_model=BarberResponse)
def patch_deactivate_barber(
    barber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("barberos.eliminar"))
):
    result, error = deactivate_barber(db, barber_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result
