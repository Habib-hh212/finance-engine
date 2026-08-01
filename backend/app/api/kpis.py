import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.kpi import KPIResponse
from app.services import kpis

router = APIRouter(tags=["kpis"])


@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    company_id: uuid.UUID,
    fiscal_year: Optional[int] = Query(None, description="Scopes budget utilization to this fiscal year"),
    cash_start_period: Optional[date] = Query(None, description="Anchor month for cash runway; omit to skip that KPI"),
    cash_opening_balance: float = Query(0.0),
    db: Session = Depends(get_db),
):
    result = kpis.compute_kpis(
        db,
        company_id,
        fiscal_year=fiscal_year,
        cash_start_period=cash_start_period,
        cash_opening_balance=cash_opening_balance,
    )
    return KPIResponse(**result.__dict__)
