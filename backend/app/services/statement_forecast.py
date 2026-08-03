"""Financial Statement Forecasting: projects the Income Statement and
Balance Sheet forward using driver linkages, not just a report on actuals.

Revenue driver: the existing per-product sales forecast (the same
exponential-smoothing model the Cash Flow Forecast module already uses),
summed by calendar month.

Expense driver: APPROVED budget lines whose GL account is categorized
"expense", summed by calendar month. Deliberately not filtered by
Budget.type (unlike the Cash Flow Forecast's narrower "type == expense"
cash-out definition) -- an expense line can legitimately live on any
budget type (zero-based, flexible, etc.), and the underlying GL account
category is the correct signal for "is this an income-statement expense."

Balance Sheet drivers:
- Accounts Receivable = forecasted revenue for the period, converted to a
  balance via Days Sales Outstanding: AR = revenue / 30 * dso_days,
  approximating a month as 30 days (the same simplification the Cash Flow
  Forecast module already uses for its collection lag).
- Accounts Payable = forecasted expense for the period via Days Payable
  Outstanding, same approximation.
- Cash = the existing Cash Flow Forecast module's closing balance per
  period, seeded from the actual balance of GL accounts tagged
  forecast_role="cash" as of the day before the forecast starts.
- Equity = the actual total equity as of the day before the forecast
  starts, rolled forward by adding each period's forecasted net income.
  This assumes no dividends or capital transactions during the horizon --
  neither is modeled anywhere in this system, so assuming they're zero is
  the honest baseline rather than a guess.
- Every other asset/liability account (not tagged cash/AR/AP) is carried
  forward flat at its last actual balance -- there's no driver for it, so
  "unchanged" is the honest choice, not a guess.

As with the historical Balance Sheet, there's no double-entry enforcement
anywhere in this system, so `is_balanced`/`difference` report whether the
projection balances rather than assuming it does. Unlike the historical
report, a projection difference here is informative on its own: since
assets/liabilities are driven independently from equity (which only rolls
forward net income), the gap is the projection's implied financing need
(or surplus) -- not just a data-entry inconsistency.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Budget, BudgetLine, GLAccount, SalesActual
from app.services import cashflow
from app.services.financial_statements import balance_sheet as historical_balance_sheet

DAYS_PER_MONTH = 30
BALANCE_TOLERANCE = 0.01


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _sales_forecast_periods_needed(db: Session, company_id, start_period: date, periods: int) -> int:
    """`cashflow.forecast_sales_by_month(periods)` generates `periods` months
    starting the month *after the last sales actual* -- not starting at our
    `start_period`. If the forecast is requested for a start_period further
    out than that (the common case: sales history rarely ends exactly the
    month before whatever period someone picks to forecast from), the tail
    of our target window falls outside what it generated. Request enough
    periods to cover through our actual last target month instead.
    """
    last_actual = db.query(func.max(SalesActual.period)).filter(SalesActual.company_id == company_id).scalar()
    if last_actual is None:
        return periods
    target_end = start_period + relativedelta(months=periods - 1)
    months_ahead = (target_end.year - last_actual.year) * 12 + (target_end.month - last_actual.month)
    return max(periods, months_ahead)


def _approved_expense_budget_by_month(db: Session, company_id) -> dict:
    totals: dict = {}
    rows = (
        db.query(BudgetLine)
        .join(Budget, Budget.id == BudgetLine.budget_id)
        .join(GLAccount, GLAccount.id == BudgetLine.gl_account_id)
        .filter(Budget.company_id == company_id, Budget.status == "approved", GLAccount.category == "expense")
        .all()
    )
    for line in rows:
        month = _month_start(line.period)
        totals[month] = totals.get(month, 0.0) + float(line.amount)
    return totals


@dataclass
class IncomeStatementForecastPeriod:
    period: date
    revenue_forecast: float
    expense_forecast: float
    net_profit_forecast: float


def forecast_income_statement(db: Session, company_id, start_period: date, periods: int = 12) -> list:
    start_period = _month_start(start_period)
    months = [start_period + relativedelta(months=i) for i in range(periods)]

    sales_periods = _sales_forecast_periods_needed(db, company_id, start_period, periods)
    revenue_by_month = cashflow.forecast_sales_by_month(db, company_id, sales_periods)
    expense_by_month = _approved_expense_budget_by_month(db, company_id)

    rows = []
    for month in months:
        revenue = round(revenue_by_month.get(month, 0.0), 2)
        expense = round(expense_by_month.get(month, 0.0), 2)
        rows.append(
            IncomeStatementForecastPeriod(
                period=month,
                revenue_forecast=revenue,
                expense_forecast=expense,
                net_profit_forecast=round(revenue - expense, 2),
            )
        )
    return rows


@dataclass
class BalanceSheetForecastPeriod:
    period: date
    accounts_receivable: float
    cash: float
    other_assets: float
    total_assets: float
    accounts_payable: float
    other_liabilities: float
    total_liabilities: float
    equity: float
    is_balanced: bool
    difference: float


def forecast_balance_sheet(
    db: Session,
    company_id,
    start_period: date,
    periods: int = 12,
    dso_days: float = 45,
    dpo_days: float = 30,
    collection_lag_days: int = 30,
) -> list:
    start_period = _month_start(start_period)
    as_of_actual = start_period - timedelta(days=1)

    actual = historical_balance_sheet(db, company_id, as_of_actual)
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}

    def role_of(gl_account_id) -> Optional[str]:
        account = accounts.get(gl_account_id)
        return account.forecast_role if account is not None else None

    cash_base = round(sum(line.amount for line in actual.asset_lines if role_of(line.gl_account_id) == "cash"), 2)
    other_assets_base = round(
        sum(
            line.amount
            for line in actual.asset_lines
            if role_of(line.gl_account_id) not in ("cash", "accounts_receivable")
        ),
        2,
    )
    other_liabilities_base = round(
        sum(line.amount for line in actual.liability_lines if role_of(line.gl_account_id) != "accounts_payable"),
        2,
    )

    income_rows = forecast_income_statement(db, company_id, start_period, periods)
    cash_rows = cashflow.build_forecast(
        db, company_id, start_period, periods=periods, collection_lag_days=collection_lag_days, opening_balance=cash_base
    )

    rows = []
    cumulative_net_income = 0.0
    for income_row, cash_row in zip(income_rows, cash_rows):
        cumulative_net_income += income_row.net_profit_forecast
        ar = round(income_row.revenue_forecast / DAYS_PER_MONTH * dso_days, 2)
        ap = round(income_row.expense_forecast / DAYS_PER_MONTH * dpo_days, 2)
        cash = cash_row.closing_balance
        total_assets = round(ar + cash + other_assets_base, 2)
        total_liabilities = round(ap + other_liabilities_base, 2)
        equity = round(actual.total_equity + cumulative_net_income, 2)
        difference = round(total_assets - (total_liabilities + equity), 2)
        rows.append(
            BalanceSheetForecastPeriod(
                period=income_row.period,
                accounts_receivable=ar,
                cash=cash,
                other_assets=other_assets_base,
                total_assets=total_assets,
                accounts_payable=ap,
                other_liabilities=other_liabilities_base,
                total_liabilities=total_liabilities,
                equity=equity,
                is_balanced=abs(difference) <= BALANCE_TOLERANCE,
                difference=difference,
            )
        )
    return rows
