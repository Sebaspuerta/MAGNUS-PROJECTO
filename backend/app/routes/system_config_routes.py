from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.system_config import SystemConfigCreate, SystemConfigResponse, SystemConfigUpdate
from app.services.system_config_service import (
    create_system_config,
    get_system_config_by_key,
    list_system_config,
    update_system_config
)
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/system-config",
    tags=["Configuración del Sistema"]
)


@router.get("", response_model=list[SystemConfigResponse])
def get_system_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.ver"))
):
    return list_system_config(db)


@router.get("/{key}", response_model=SystemConfigResponse)
def get_system_config_item(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.ver"))
):
    result, error = get_system_config_by_key(db, key)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result


@router.post("", response_model=SystemConfigResponse)
def post_system_config(
    payload: SystemConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.editar"))
):
    result, error = create_system_config(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.patch("/{config_id}", response_model=SystemConfigResponse)
def patch_system_config(
    config_id: int,
    payload: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.editar"))
):
    result, error = update_system_config(db, config_id, payload, current_user)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result
