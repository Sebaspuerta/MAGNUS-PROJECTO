import math
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.master_code import MasterCodeConfig
from app.models.security import User
from app.services.security_service import create_audit_log
from app.utils.security import hash_password, verify_password

_MAX_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


def _get_config(db: Session) -> MasterCodeConfig:
    cfg = db.query(MasterCodeConfig).first()
    if not cfg:
        cfg = MasterCodeConfig(failed_attempts=0)
        db.add(cfg)
        db.flush()
    return cfg


def _check_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not any(c.isalpha() for c in password):
        return "La contraseña debe contener al menos una letra."
    if not any(c.isdigit() for c in password):
        return "La contraseña debe contener al menos un número."
    return None


def set_master_code(db: Session, admin_user: User, current_password: str, master_code: str):
    if not verify_password(current_password, admin_user.password_hash):
        return None, "Contraseña actual incorrecta."

    if len(master_code) < 6:
        return None, "El código maestro debe tener al menos 6 caracteres."

    cfg = _get_config(db)
    cfg.code_hash = hash_password(master_code)
    cfg.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="seguridad",
        action="set_master_code",
        detail=f"El administrador '{admin_user.username}' definió o cambió el código maestro.",
        user_id=admin_user.id
    )

    db.commit()
    return {"detail": "Código maestro actualizado correctamente."}, None


def recover_password(
    db: Session,
    username: str,
    master_code: str,
    new_password: str,
    ip_address: str | None = None
):
    cfg = _get_config(db)

    if not cfg.code_hash:
        return None, "Recuperación no configurada. Contacta al administrador del sistema."

    now = datetime.utcnow()

    # Verificar bloqueo activo
    if cfg.locked_until and cfg.locked_until > now:
        remaining = math.ceil((cfg.locked_until - now).total_seconds() / 60)
        return None, {"code": "master_locked", "minutes_remaining": remaining}

    # Verificar código maestro
    if not verify_password(master_code, cfg.code_hash):
        cfg.failed_attempts += 1

        log_detail = (
            f"Código maestro incorrecto para recuperar '{username}'. "
            f"Intento {cfg.failed_attempts}/{_MAX_ATTEMPTS}."
        )

        if cfg.failed_attempts >= _MAX_ATTEMPTS:
            cfg.locked_until = now + timedelta(minutes=_LOCKOUT_MINUTES)
            log_detail += f" Bloqueado por {_LOCKOUT_MINUTES} min."

        create_audit_log(
            db=db,
            module="seguridad",
            action="recover_password_failed",
            detail=log_detail,
            ip_address=ip_address
        )
        db.commit()

        if cfg.failed_attempts >= _MAX_ATTEMPTS:
            return None, {"code": "master_locked", "minutes_remaining": _LOCKOUT_MINUTES}

        return None, "Datos incorrectos. Verifica el usuario y el código maestro."

    # Código correcto — validar fuerza de contraseña antes de tocar el usuario
    strength_error = _check_password_strength(new_password)
    if strength_error:
        return None, strength_error

    # Buscar usuario (el código ya está validado; no tocamos el contador por problemas de usuario)
    user = db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
    if not user:
        create_audit_log(
            db=db,
            module="seguridad",
            action="recover_password_failed",
            detail=f"Recuperación fallida: usuario '{username}' no existe o está inactivo.",
            ip_address=ip_address
        )
        db.commit()
        return None, "No se pudo completar la recuperación. Verifica el nombre de usuario."

    # Cambiar contraseña
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.utcnow()
    user.must_change_password = False
    user.updated_at = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None

    # Reiniciar contador del código maestro
    cfg.failed_attempts = 0
    cfg.locked_until = None

    create_audit_log(
        db=db,
        module="seguridad",
        action="recover_password",
        detail=f"Contraseña del usuario '{user.username}' recuperada con código maestro.",
        ip_address=ip_address,
        user_id=user.id
    )

    db.commit()
    return {"detail": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}, None
