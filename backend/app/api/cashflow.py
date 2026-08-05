import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import CashItem, User
from app.schemas.cashflow import CashFlowForecastResponse, CashFlowPeriodOut, CashItemCreate, CashItemOut, CashItemUpdate
from app.services import audit, cashflow

router = APIRouter(prefix="/cashflow", tags=["cashflow"])


@router.post("/items", response_model=CashItemOut)
def create_cash_item( payload: CashItemCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    item = CashItem(company_id=company_id, **payload.model_dump())
    db.add(item)
    db.flush()
    audit.record(
        db, company_id, "cash_item", item.id, "create", current_user, f"Added a {item.direction} cash item of {item.amount} {item.currency} for {item.period}"
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[CashItemOut])
def list_cash_items(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(CashItem).filter(CashItem.company_id == company_id).order_by(CashItem.period.desc()).all()


def _get_cash_item_or_404(db: Session, company_id: uuid.UUID, item_id: uuid.UUID) -> CashItem:
    item = db.query(CashItem).filter(CashItem.id == item_id, CashItem.company_id == company_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Cash item not found")
    return item


@router.patch("/items/{item_id}", response_model=CashItemOut)
def update_cash_item(
    item_id: uuid.UUID,
    payload: CashItemUpdate,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    item = _get_cash_item_or_404(db, company_id, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    audit.record(db, company_id, "cash_item", item.id, "update", current_user, f"Edited a cash item ({item.amount} {item.currency}, {item.period})")
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=204)
def delete_cash_item( item_id: uuid.UUID,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    item = _get_cash_item_or_404(db, company_id, item_id)
    audit.record(db, company_id, "cash_item", item.id, "delete", current_user, f"Deleted a cash item ({item.amount} {item.currency}, {item.period})")
    db.delete(item)
    db.commit()


@router.get("/forecast", response_model=CashFlowForecastResponse)
def get_cash_flow_forecast(
    company_id: uuid.UUID = Depends(require_company_access),
    start_period: date = Query(..., description="First month of the forecast, e.g. 2026-08-01"),
    periods: int = Query(12, ge=1, le=24),
    collection_lag_days: int = Query(30, ge=0, le=365, description="Days between a forecasted sale and expected cash receipt"),
    opening_balance: float = Query(0.0),
    db: Session = Depends(get_db)):
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
