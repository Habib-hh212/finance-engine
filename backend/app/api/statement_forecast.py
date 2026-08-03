import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.statement_forecast import BalanceSheetForecastPeriodOut, IncomeStatementForecastPeriodOut
from app.services import statement_forecast

router = APIRouter(prefix="/forecast", tags=["statement-forecast"])


@router.get("/income-statement", response_model=list[IncomeStatementForecastPeriodOut])
def get_income_statement_forecast(
    company_id: uuid.UUID,
    start_period: date,
    periods: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
):
    rows = statement_forecast.forecast_income_statement(db, company_id, start_period, periods)
    return [IncomeStatementForecastPeriodOut(**row.__dict__) for row in rows]


@router.get("/balance-sheet", response_model=list[BalanceSheetForecastPeriodOut])
def get_balance_sheet_forecast(
    company_id: uuid.UUID,
    start_period: date,
    periods: int = Query(12, ge=1, le=36),
    dso_days: float = 45,
    dpo_days: float = 30,
    collection_lag_days: int = 30,
    db: Session = Depends(get_db),
):
    rows = statement_forecast.forecast_balance_sheet(
        db, company_id, start_period, periods, dso_days=dso_days, dpo_days=dpo_days, collection_lag_days=collection_lag_days
    )
    return [BalanceSheetForecastPeriodOut(**row.__dict__) for row in rows]
