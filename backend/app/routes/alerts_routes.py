from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.alert import AlertCreate, AlertResponse
from app.services.alert_service import create_alert, generate_system_alerts, list_alerts, mark_alert_as_read
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/alerts",
    tags=["Alertas"]
)


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    only_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("alertas.ver"))
):
    return list_alerts(db, only_active=only_active)


@router.post("/generate")
def post_generate_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("alertas.ver"))
):
    result, error = generate_system_alerts(db, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.post("", response_model=AlertResponse)
def post_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("alertas.ver"))
):
    result, error = create_alert(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.patch("/{alert_id}/read", response_model=AlertResponse)
def patch_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("alertas.ver"))
):
    result, error = mark_alert_as_read(db, alert_id, current_user)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result
