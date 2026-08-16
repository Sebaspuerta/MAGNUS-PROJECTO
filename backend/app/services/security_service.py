import math
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import settings
from app.models.security import AuditLog, Permission, Role, RolePermission, User
from app.schemas.security import UserCreate
from app.utils.security import create_access_token, hash_password, verify_password


OFFICIAL_ROLES = [
    ("Administrador", "Acceso total al sistema."),
    ("Barbero", "Gestiona atención, clientes y comandas operativas."),
    ("Cajero", "Gestiona pagos, caja, cierres y cuentas por cobrar."),
    ("Consultor", "Solo consulta dashboard, reportes e históricos.")
]


OFFICIAL_MODULE_ACTIONS = {
    "seguridad": ["ver", "crear", "editar", "eliminar"],
    "barberos": ["ver", "crear", "editar", "eliminar"],
    "clientes": ["ver", "crear", "editar", "eliminar"],
    "servicios": ["ver", "crear", "editar", "eliminar"],
    "comandas": ["ver", "crear", "editar", "eliminar", "cerrar"],
    "inventario": ["ver", "crear", "editar", "eliminar", "ajustar"],
    "cuentas_por_cobrar": ["ver", "crear", "editar", "abonar"],
    "alertas": ["ver"],
    "caja": ["ver", "abrir", "cerrar", "movimiento"],
    "reportes": ["ver", "exportar"],
    "dashboard": ["ver"],
    "auditoria": ["ver"]
}


def create_audit_log(
    db: Session,
    module: str,
    action: str,
    detail: str | None = None,
    user_id: int | None = None,
    ip_address: str | None = None
):
    log = AuditLog(
        user_id=user_id,
        module=module,
        action=action,
        detail=detail,
        ip_address=ip_address
    )
    db.add(log)


def seed_initial_security(db: Session):
    roles_by_name = {}

    for role_name, description in OFFICIAL_ROLES:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description=description)
            db.add(role)
            db.flush()
        roles_by_name[role_name] = role

    permissions_by_code = {}

    for module, actions in OFFICIAL_MODULE_ACTIONS.items():
        for action in actions:
            code = f"{module}.{action}"
            permission = db.query(Permission).filter(Permission.code == code).first()
            if not permission:
                permission = Permission(
                    module=module,
                    action=action,
                    code=code,
                    description=f"Permite {action} en el módulo {module}."
                )
                db.add(permission)
                db.flush()
            permissions_by_code[code] = permission

    administrador = roles_by_name["Administrador"]
    for permission in permissions_by_code.values():
        exists = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == administrador.id,
                RolePermission.permission_id == permission.id
            )
            .first()
        )
        if not exists:
            db.add(RolePermission(role_id=administrador.id, permission_id=permission.id))

    role_permissions = {
        "Barbero": [
            "dashboard.ver",
            "clientes.ver", "clientes.crear", "clientes.editar",
            "servicios.ver",
            "comandas.ver", "comandas.crear", "comandas.editar", "comandas.cerrar",
            "inventario.ver",
            "caja.ver", "caja.abrir",
        ],
        "Cajero": [
            "dashboard.ver",
            "clientes.ver", "clientes.crear", "clientes.editar",
            "servicios.ver",
            "comandas.ver", "comandas.crear", "comandas.editar", "comandas.cerrar",
            "caja.ver", "caja.abrir", "caja.cerrar", "caja.movimiento",
            "cuentas_por_cobrar.ver", "cuentas_por_cobrar.crear", "cuentas_por_cobrar.editar", "cuentas_por_cobrar.abonar",
            "alertas.ver",
            "reportes.ver"
        ],
        "Consultor": [
            "dashboard.ver",
            "clientes.ver",
            "barberos.ver",
            "servicios.ver",
            "inventario.ver",
            "cuentas_por_cobrar.ver",
            "alertas.ver",
            "caja.ver",
            "reportes.ver"
        ]
    }

    for role_name, permission_codes in role_permissions.items():
        role = roles_by_name[role_name]
        for code in permission_codes:
            permission = permissions_by_code.get(code)
            if not permission:
                continue

            exists = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id
                )
                .first()
            )
            if not exists:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    admin_username = settings.admin_username or "admin"
    admin_password = settings.admin_password or "admin123"
    admin_full_name = settings.admin_full_name or "Administrador MAGNUS"

    admin_user = db.query(User).filter(User.username == admin_username).first()
    if not admin_user:
        admin_user = User(
            username=admin_username,
            full_name=admin_full_name,
            password_hash=hash_password(admin_password),
            role_id=administrador.id,
            is_active=True,
            must_change_password=True
        )
        db.add(admin_user)
        db.flush()

        create_audit_log(
            db=db,
            module="seguridad",
            action="seed_admin",
            detail=f"Usuario administrador inicial {admin_username} creado.",
            user_id=admin_user.id
        )

    db.commit()


def authenticate_user(db: Session, username: str, password: str, ip_address: str | None = None):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None, "Usuario o contraseña incorrectos."

    if not user.is_active:
        return None, "Usuario inactivo."

    now = datetime.utcnow()

    if user.locked_until and user.locked_until > now:
        remaining_secs = (user.locked_until - now).total_seconds()
        return None, {
            "code": "account_locked",
            "minutes_remaining": math.ceil(remaining_secs / 60)
        }

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            create_audit_log(
                db=db,
                module="seguridad",
                action="bloqueo_login",
                detail=f"Usuario {user.username} bloqueado por 5 intentos fallidos.",
                user_id=user.id,
                ip_address=ip_address
            )

        db.commit()
        return None, "Usuario o contraseña incorrectos."

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    create_audit_log(
        db=db,
        module="seguridad",
        action="login",
        detail=f"Inicio de sesión correcto para {user.username}.",
        user_id=user.id,
        ip_address=ip_address
    )

    db.commit()
    db.refresh(user)

    token = create_access_token({
        "sub": user.username,
        "role": user.role.name,
        "user_id": user.id
    })

    return {
        "access_token": token,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.name,
        "must_change_password": bool(user.must_change_password)
    }, None


def list_roles(db: Session):
    return db.query(Role).filter(Role.is_active == True).order_by(Role.id.asc()).all()


def list_users(db: Session):
    users = db.query(User).join(Role).order_by(User.id.asc()).all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.name,
            "is_active": user.is_active
        }
        for user in users
    ]


def create_user(db: Session, payload: UserCreate, admin_user: User):
    existing_user = db.query(User).filter(User.username == payload.username).first()

    if existing_user:
        return None, "Ya existe un usuario con ese nombre de usuario."

    role = db.query(Role).filter(Role.name == payload.role_name, Role.is_active == True).first()

    if not role:
        return None, "El rol indicado no existe o está inactivo."

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        is_active=True,
        password_changed_at=datetime.utcnow()
    )

    db.add(user)
    db.flush()

    create_audit_log(
        db=db,
        module="seguridad",
        action="crear_usuario",
        detail=f"El administrador {admin_user.username} creó el usuario {user.username}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.name,
        "is_active": user.is_active
    }, None


def deactivate_user(db: Session, user_id: int, admin_user: User):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return None, "Usuario no encontrado."

    if user.username == "admin":
        return None, "No se puede desactivar el usuario administrador inicial."

    user.is_active = False
    user.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="seguridad",
        action="desactivar_usuario",
        detail=f"El administrador {admin_user.username} desactivó el usuario {user.username}.",
        user_id=admin_user.id
    )

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.name,
        "is_active": user.is_active
    }, None


def change_password(db: Session, current_user: User, current_password: str, new_password: str):
    if not verify_password(current_password, current_user.password_hash):
        return None, "La contraseña actual es incorrecta."

    if len(new_password) < 6:
        return None, "La nueva contraseña debe tener al menos 6 caracteres."

    if verify_password(new_password, current_user.password_hash):
        return None, "La nueva contraseña no puede ser igual a la actual."

    current_user.password_hash = hash_password(new_password)
    current_user.password_changed_at = datetime.utcnow()
    current_user.must_change_password = False
    current_user.updated_at = datetime.utcnow()

    create_audit_log(
        db=db,
        module="seguridad",
        action="cambiar_password",
        detail=f"El usuario {current_user.username} cambió su contraseña.",
        user_id=current_user.id
    )

    db.commit()
    db.refresh(current_user)

    return {"detail": "Contraseña actualizada correctamente."}, None
