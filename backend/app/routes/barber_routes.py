from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.barber import BarberCreate, BarberResponse, BarberUpdate, BarberUserPasswordRequest
from app.services.barber_service import (
    create_barber,
    create_barber_user,
    deactivate_barber,
    get_barber_by_id,
    get_barber_performance,
    get_barber_user_info,
    list_barbers,
    reset_barber_password,
    toggle_barber_access,
    update_barber
)
from app.utils.security import get_current_user, require_admin, require_permission


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


@router.get("/{barber_id}/performance")
def get_barber_performance_route(
    barber_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("barberos.ver"))
):
    result, error = get_barber_performance(db, barber_id, start_date, end_date)

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


# ── Gestión de usuarios de barbero (solo Administrador) ──────────────────────

@router.get("/{barber_id}/user-info")
def get_barber_user_info_route(
    barber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = get_barber_user_info(db, barber_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result


@router.post("/{barber_id}/create-user")
def post_create_barber_user(
    barber_id: int,
    payload: BarberUserPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = create_barber_user(db, barber_id, payload.password, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.put("/{barber_id}/reset-password")
def put_reset_barber_password(
    barber_id: int,
    payload: BarberUserPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = reset_barber_password(db, barber_id, payload.password, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.put("/{barber_id}/toggle-access")
def put_toggle_barber_access(
    barber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result, error = toggle_barber_access(db, barber_id, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result
