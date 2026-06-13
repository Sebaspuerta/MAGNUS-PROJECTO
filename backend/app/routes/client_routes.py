from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate
from app.services.client_service import (
    create_client,
    deactivate_client,
    get_client_by_id,
    get_client_profile,
    list_clients,
    update_client
)
from app.utils.security import get_current_user, require_permission


router = APIRouter(
    prefix="/api/clients",
    tags=["Gestión de Clientes"]
)


@router.get("", response_model=list[ClientResponse])
def get_clients(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clientes.ver"))
):
    return list_clients(db, include_inactive=include_inactive)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clientes.ver"))
):
    result, error = get_client_by_id(db, client_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.get("/{client_id}/profile")
def get_client_profile_route(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clientes.ver"))
):
    result, error = get_client_profile(db, client_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result


@router.post("", response_model=ClientResponse)
def post_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clientes.crear"))
):
    result, error = create_client(db, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{client_id}", response_model=ClientResponse)
def patch_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clientes.editar"))
):
    result, error = update_client(db, client_id, payload, current_user)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return result


@router.patch("/{client_id}/deactivate", response_model=ClientResponse)
def patch_deactivate_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clientes.eliminar"))
):
    result, error = deactivate_client(db, client_id, current_user)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result
