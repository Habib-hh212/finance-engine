import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.statement_forecast import BalanceSheetForecastPeriodOut, IncomeStatementForecastPeriodOut
from app.services import statement_forecast
from app.services.excel_export import sheets_to_xlsx_response

router = APIRouter(prefix="/forecast", tags=["statement-forecast"])


@router.get("/income-statement", response_model=list[IncomeStatementForecastPeriodOut])
def get_income_statement_forecast(
    company_id: uuid.UUID,
    start_period: date,
    periods: int = Query(12, ge=1, le=36),
    forecast_method: Literal["driver_based", "historical_trend"] = "driver_based",
    trend_model: str = Query(
        "exponential_smoothing",
        description="Only used when forecast_method=historical_trend: moving_average | weighted_average | "
        "exponential_smoothing | random_forest | gradient_boosting",
    ),
    db: Session = Depends(get_db),
):
    if forecast_method == "historical_trend":
        try:
            rows = statement_forecast.forecast_income_statement_from_history(
                db, company_id, start_period, periods, model=trend_model
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
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


@router.get("/export")
def export_statement_forecast(
    company_id: uuid.UUID,
    start_period: date,
    periods: int = Query(12, ge=1, le=36),
    forecast_method: Literal["driver_based", "historical_trend"] = "driver_based",
    trend_model: str = "exponential_smoothing",
    dso_days: float = 45,
    dpo_days: float = 30,
    collection_lag_days: int = 30,
    db: Session = Depends(get_db),
):
    if forecast_method == "historical_trend":
        try:
            income_rows = statement_forecast.forecast_income_statement_from_history(
                db, company_id, start_period, periods, model=trend_model
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        balance_rows = []
    else:
        income_rows = statement_forecast.forecast_income_statement(db, company_id, start_period, periods)
        balance_rows = statement_forecast.forecast_balance_sheet(
            db, company_id, start_period, periods, dso_days=dso_days, dpo_days=dpo_days, collection_lag_days=collection_lag_days
        )

    income_sheet = [
        {
            "Period": r.period,
            "Revenue": r.revenue_forecast,
            "Expense": r.expense_forecast,
            "Net Profit": r.net_profit_forecast,
        }
        for r in income_rows
    ]
    sheets = {"Income Statement Forecast": income_sheet}
    if balance_rows:
        sheets["Balance Sheet Forecast"] = [
            {
                "Period": r.period,
                "Accounts Receivable": r.accounts_receivable,
                "Cash": r.cash,
                "Other Assets": r.other_assets,
                "Total Assets": r.total_assets,
                "Accounts Payable": r.accounts_payable,
                "Other Liabilities": r.other_liabilities,
                "Total Liabilities": r.total_liabilities,
                "Equity": r.equity,
                "Balanced": r.is_balanced,
            }
            for r in balance_rows
        ]
    return sheets_to_xlsx_response(sheets, f"statement-forecast-{start_period}.xlsx")
