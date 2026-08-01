import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CashItem
from app.schemas.cashflow import CashFlowForecastResponse, CashFlowPeriodOut, CashItemCreate, CashItemOut
from app.services import cashflow

router = APIRouter(prefix="/cashflow", tags=["cashflow"])


@router.post("/items", response_model=CashItemOut)
def create_cash_item(company_id: uuid.UUID, payload: CashItemCreate, db: Session = Depends(get_db)):
    item = CashItem(company_id=company_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[CashItemOut])
def list_cash_items(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(CashItem).filter(CashItem.company_id == company_id).all()


@router.get("/forecast", response_model=CashFlowForecastResponse)
def get_cash_flow_forecast(
    company_id: uuid.UUID,
    start_period: date = Query(..., description="First month of the forecast, e.g. 2026-08-01"),
    periods: int = Query(12, ge=1, le=24),
    collection_lag_days: int = Query(30, ge=0, le=365, description="Days between a forecasted sale and expected cash receipt"),
    opening_balance: float = Query(0.0),
    db: Session = Depends(get_db),
):
    rows = cashflow.build_forecast(
        db,
        company_id,
        start_period=start_period,
        periods=periods,
        collection_lag_days=collection_lag_days,
        opening_balance=opening_balance,
    )
    return CashFlowForecastResponse(
        company_id=company_id,
        start_period=start_period,
        periods=periods,
        collection_lag_days=collection_lag_days,
        rows=[
            CashFlowPeriodOut(
                period=r.period,
                cash_in_forecast=r.cash_in_forecast,
                cash_in_manual=r.cash_in_manual,
                cash_in_total=r.cash_in_total,
                cash_out_budget=r.cash_out_budget,
                cash_out_manual=r.cash_out_manual,
                cash_out_total=r.cash_out_total,
                net_cash_flow=r.net_cash_flow,
                opening_balance=r.opening_balance,
                closing_balance=r.closing_balance,
            )
            for r in rows
        ],
    )
