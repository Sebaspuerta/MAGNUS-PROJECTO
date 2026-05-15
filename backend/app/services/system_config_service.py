from datetime import datetime
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.models.security import User
from app.schemas.system_config import SystemConfigCreate, SystemConfigUpdate
from app.services.security_service import create_audit_log


def serialize_system_config(config: SystemConfig):
    return {
        "id": config.id,
        "key": config.key,
        "value": config.value,
        "description": config.description,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }


def list_system_config(db: Session):
    return [serialize_system_config(config) for config in db.query(SystemConfig).order_by(SystemConfig.id.asc()).all()]


def get_system_config_by_key(db: Session, key: str):
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        return None, "Configuración no encontrada."
    return serialize_system_config(config), None


def create_system_config(db: Session, payload: SystemConfigCreate, current_user: User):
    existing = db.query(SystemConfig).filter(SystemConfig.key == payload.key).first()
    if existing:
        return None, "La clave de configuración ya existe." 

    config = SystemConfig(
        key=payload.key,
        value=payload.value,
        description=payload.description
    )
    db.add(config)
    db.flush()

    create_audit_log(
        db=db,
        module="seguridad",
        action="crear_configuracion",
        detail=f"El usuario {current_user.username} creó la configuración {config.key}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(config)
    return serialize_system_config(config), None


def update_system_config(db: Session, config_id: int, payload: SystemConfigUpdate, current_user: User):
    config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if not config:
        return None, "Configuración no encontrada."

    if payload.value is not None:
        config.value = payload.value
    if payload.description is not None:
        config.description = payload.description

    config.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="seguridad",
        action="editar_configuracion",
        detail=f"El usuario {current_user.username} actualizó la configuración {config.key}.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(config)
    return serialize_system_config(config), None
