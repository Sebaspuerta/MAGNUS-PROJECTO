from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.security import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RoleResponse,
    UserCreate,
    UserResponse
)
from app.services.security_service import (
    authenticate_user,
    change_password,
    create_user,
    deactivate_user,
    list_roles,
    list_users
)
from app.utils.security import get_current_user, require_permission


router = APIRouter(
    prefix="/api/security",
    tags=["Seguridad y Control de Acceso"]
)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else None

    result, error = authenticate_user(
        db=db,
        username=payload.username,
        password=payload.password,
        ip_address=ip_address
    )

    if error:
        raise HTTPException(status_code=401, detail=error)

    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "username": result["username"],
        "full_name": result["full_name"],
        "role": result["role"]
    }


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role.name,
        "is_active": current_user.is_active
    }


@router.post("/change-password")
def post_change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result, error = change_password(
        db, current_user, payload.current_password, payload.new_password
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.get("/roles", response_model=list[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.ver"))
):
    return list_roles(db)


@router.get("/users", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.ver"))
):
    return list_users(db)


@router.post("/users", response_model=UserResponse)
def post_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.crear"))
):
    result, error = create_user(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/users/{user_id}/deactivate", response_model=UserResponse)
def patch_deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("seguridad.eliminar"))
):
    result, error = deactivate_user(db, user_id, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result
