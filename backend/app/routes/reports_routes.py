from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.security import User
from app.services.reports_service import (
    accounts_receivable_report,
    cash_closings,
    sales_by_barber,
    sales_by_period,
    top_products
)
from app.utils.security import require_permission


router = APIRouter(
    prefix="/api/reports",
    tags=["Reportes"]
)


@router.get("/sales-by-period")
def get_sales_by_period(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reportes.ver"))
):
    return sales_by_period(db, start_date, end_date)


@router.get("/sales-by-barber")
def get_sales_by_barber(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reportes.ver"))
):
    return sales_by_barber(db, start_date, end_date)


@router.get("/top-products")
def get_top_products(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reportes.ver"))
):
    return top_products(db, start_date, end_date, limit)


@router.get("/accounts-receivable")
def get_accounts_receivable_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reportes.ver"))
):
    return accounts_receivable_report(db)


@router.get("/cash-closings")
def get_cash_closings(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reportes.ver"))
):
    return cash_closings(db, start_date, end_date)
