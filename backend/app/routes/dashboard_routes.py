from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.services.dashboard_service import get_dashboard_summary
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
    return get_dashboard_summary(db)
