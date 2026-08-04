import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ExchangeRate, User
from app.schemas.fx import ExchangeRateCreate, ExchangeRateOut, FxScenarioOut
from app.services import audit, fx_scenario

router = APIRouter(tags=["fx"])


@router.post("/exchange-rates", response_model=ExchangeRateOut)
def upsert_exchange_rate(
    payload: ExchangeRateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    existing = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == payload.from_currency,
            ExchangeRate.to_currency == payload.to_currency,
            ExchangeRate.rate_date == payload.rate_date,
        )
        .first()
    )
    if existing is not None:
        existing.rate = payload.rate
        rate = existing
        action, summary = "update", f"Updated {payload.from_currency}->{payload.to_currency} rate for {payload.rate_date} to {payload.rate}"
    else:
        rate = ExchangeRate(**payload.model_dump())
        db.add(rate)
        db.flush()
        action, summary = "create", f"Recorded {payload.from_currency}->{payload.to_currency} rate for {payload.rate_date}: {payload.rate}"

    # Exchange rates aren't company-scoped, but the audit trail is -- record
    # against no specific company (None) rather than pretending one owns it.
    audit.record(db, None, "exchange_rate", rate.id, action, current_user, summary)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/exchange-rates", response_model=list[ExchangeRateOut])
def list_exchange_rates(
    from_currency: Optional[str] = Query(None),
    to_currency: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ExchangeRate)
    if from_currency is not None:
        query = query.filter(ExchangeRate.from_currency == from_currency)
    if to_currency is not None:
        query = query.filter(ExchangeRate.to_currency == to_currency)
    return query.order_by(ExchangeRate.rate_date.desc()).all()


@router.get("/fx/scenario", response_model=FxScenarioOut)
def get_fx_scenario(
    company_id: uuid.UUID,
    start_period: date = Query(...),
    end_period: date = Query(...),
    shock_pct: float = Query(0.0, description="Hypothetical %% move in the FX rate, e.g. -10 for a 10%% depreciation"),
    db: Session = Depends(get_db),
):
    result = fx_scenario.simulate_fx_scenario(db, company_id, start_period, end_period, shock_pct)
    return FxScenarioOut(**result.__dict__)
