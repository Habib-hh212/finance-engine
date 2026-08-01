"""Four KPIs pulled from the four full Phase 1 modules — deliberately not the
full ratio suite from the roadmap (current ratio, ROE, DSO, etc. all need a
Balance Sheet / AR-AP module that doesn't exist yet; that's Phase 2+).
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Budget, Product, SalesActual
from app.services import cashflow, forecasting, profitability, variance

MIN_BACKTEST_HISTORY = 3


@dataclass
class KPISet:
    gross_margin_pct: Optional[float]
    budget_utilization_pct: Optional[float]
    forecast_accuracy_mape: Optional[float]
    cash_runway_months: Optional[int]


def gross_margin_pct(db: Session, company_id) -> Optional[float]:
    rows = profitability.by_product(db, company_id)
    priced_rows = [r for r in rows if r.contribution_margin_total is not None]
    if not priced_rows:
        return None
    total_revenue = sum(r.revenue for r in priced_rows)
    total_contribution = sum(r.contribution_margin_total for r in priced_rows)
    if not total_revenue:
        return None
    return round((total_contribution / total_revenue) * 100, 1)


def budget_utilization_pct(db: Session, company_id, fiscal_year: Optional[int] = None) -> Optional[float]:
    query = db.query(Budget).filter(Budget.company_id == company_id, Budget.status == "approved")
    if fiscal_year is not None:
        query = query.filter(Budget.fiscal_year == fiscal_year)
    budgets = query.all()
    if not budgets:
        return None

    total_budget = 0.0
    total_spent = 0.0
    for budget in budgets:
        consumption = variance.budget_consumption(db, budget)
        total_budget += consumption.budget_amount
        total_spent += consumption.spent
    if not total_budget:
        return None
    return round((total_spent / total_budget) * 100, 1)


def forecast_accuracy_mape(db: Session, company_id, model: str = "exponential_smoothing") -> Optional[float]:
    """Walk-forward backtest: for each point after the warmup window, forecast
    one period ahead using only the data available up to that point, and
    compare to what actually happened. This is a real accuracy measurement
    against history, not a guess."""
    products = db.query(Product).filter(Product.company_id == company_id).all()
    errors = []

    for product in products:
        actuals = (
            db.query(SalesActual)
            .filter(SalesActual.company_id == company_id, SalesActual.product_id == product.id)
            .order_by(SalesActual.period)
            .all()
        )
        if len(actuals) < MIN_BACKTEST_HISTORY + 1:
            continue

        amounts = [float(a.amount) for a in actuals]
        periods = [a.period for a in actuals]
        for t in range(MIN_BACKTEST_HISTORY, len(amounts)):
            history = pd.Series(amounts[:t], index=periods[:t])
            predicted = forecasting.forecast(history, model=model, periods=1)[0].forecast
            actual = amounts[t]
            if actual == 0:
                continue
            errors.append(abs(actual - predicted) / abs(actual))

    if not errors:
        return None
    return round((sum(errors) / len(errors)) * 100, 1)


def cash_runway_months(
    db: Session,
    company_id,
    start_period: date,
    opening_balance: float = 0.0,
    window_months: int = 12,
) -> Optional[int]:
    """Months of positive cash before the running balance would go negative,
    within the forecast window. None means it doesn't go negative in that window."""
    rows = cashflow.build_forecast(db, company_id, start_period=start_period, periods=window_months, opening_balance=opening_balance)
    for i, row in enumerate(rows):
        if row.closing_balance < 0:
            return i
    return None


def compute_kpis(
    db: Session,
    company_id,
    fiscal_year: Optional[int] = None,
    cash_start_period: Optional[date] = None,
    cash_opening_balance: float = 0.0,
) -> KPISet:
    runway = None
    if cash_start_period is not None:
        runway = cash_runway_months(db, company_id, cash_start_period, cash_opening_balance)

    return KPISet(
        gross_margin_pct=gross_margin_pct(db, company_id),
        budget_utilization_pct=budget_utilization_pct(db, company_id, fiscal_year),
        forecast_accuracy_mape=forecast_accuracy_mape(db, company_id),
        cash_runway_months=runway,
    )
