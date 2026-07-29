from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.services.dashboard_service import get_dashboard_summary, get_my_cuts_today
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.ver"))
):
    # Un Barbero no debe recibir cifras de dinero/caja/fiados, ni siquiera en
    # crudo vía API. Usa /mis-cortes-hoy para su panel de inicio.
    if current_user.role.name == "Barbero":
        raise HTTPException(
            status_code=403,
            detail="Los barberos no tienen acceso al resumen financiero. Usa /api/dashboard/mis-cortes-hoy."
        )

    return get_dashboard_summary(db)


@router.get("/mis-cortes-hoy")
def get_my_cuts_today_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.ver"))
):
    return get_my_cuts_today(db, current_user.id)
