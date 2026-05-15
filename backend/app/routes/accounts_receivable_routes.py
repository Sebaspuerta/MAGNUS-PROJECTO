from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.schemas.accounts_receivable import (
    AccountsReceivableCreate,
    AccountsReceivablePaymentCreate,
    AccountsReceivableResponse
)
from app.services.accounts_receivable_service import (
    add_accounts_receivable_payment,
    create_accounts_receivable,
    get_accounts_receivable_by_id,
    list_accounts_receivable
)
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/accounts-receivable",
    tags=["Cuentas por Cobrar"]
)


@router.get("", response_model=list[AccountsReceivableResponse])
def get_accounts_receivable(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("cuentas_por_cobrar.ver"))
):
    return list_accounts_receivable(db, client_id=client_id)


@router.get("/{ar_id}", response_model=AccountsReceivableResponse)
def get_account_receivable(
    ar_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("cuentas_por_cobrar.ver"))
):
    result, error = get_accounts_receivable_by_id(db, ar_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return result


@router.post("", response_model=AccountsReceivableResponse)
def post_account_receivable(
    payload: AccountsReceivableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("cuentas_por_cobrar.crear"))
):
    result, error = create_accounts_receivable(db, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.post("/{ar_id}/payments", response_model=AccountsReceivableResponse)
def post_accounts_receivable_payment(
    ar_id: int,
    payload: AccountsReceivablePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("cuentas_por_cobrar.abonar"))
):
    result, error = add_accounts_receivable_payment(db, ar_id, payload, current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result
