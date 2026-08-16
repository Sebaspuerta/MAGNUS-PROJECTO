from fastapi import APIRouter, Depends
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
    summary = get_dashboard_summary(db)

    # Un Barbero no debe recibir cifras de dinero/fiados/inventario, ni
    # siquiera en crudo vía API (usa /mis-cortes-hoy para su panel de
    # inicio). La única excepción es el estado de caja (abierta o no, y
    # desde cuándo) sin montos, para el atajo de "Abrir caja" del
    # Dashboard — ahora que el rol Barbero tiene permiso caja.abrir.
    if current_user.role.name == "Barbero":
        cash = summary["cash"]
        return {
            "cash": {
                "has_open_register": cash["has_open_register"],
                "opened_at": cash["opened_at"]
            }
        }

    return summary


@router.get("/mis-cortes-hoy")
def get_my_cuts_today_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.ver"))
):
    return get_my_cuts_today(db, current_user.id)
