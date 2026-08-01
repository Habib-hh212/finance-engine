"""Rolling cash flow forecast, driven off two upstream modules plus manual entries:

- Cash IN: forecasted sales revenue (exponential smoothing, per product, summed
  by calendar month), shifted forward by an expected receivable-collection lag.
- Cash OUT: approved expense-budget lines (status == 'approved'), summed by
  their budgeted month. Draft/pending budgets are excluded on purpose — an
  unapproved budget isn't a commitment yet.
- Both are topped up with manually entered CashItem rows (payroll, vendor
  payments, tax, loan draws/repayments, interest, or ad-hoc receivable
  adjustments) for cash movements the two drivers above don't cover.

Phase 1 assumes every contributing amount is already in the company's base
currency — cross-currency conversion via ExchangeRate is a Phase 4 item.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models import Budget, BudgetLine, CashItem, Product, SalesActual
from app.services import forecasting


@dataclass
class CashFlowPeriod:
    period: date
    cash_in_forecast: float = 0.0
    cash_in_manual: float = 0.0
    cash_out_budget: float = 0.0
    cash_out_manual: float = 0.0
    opening_balance: float = 0.0
    closing_balance: float = 0.0

    @property
    def cash_in_total(self) -> float:
        return round(self.cash_in_forecast + self.cash_in_manual, 2)

    @property
    def cash_out_total(self) -> float:
        return round(self.cash_out_budget + self.cash_out_manual, 2)

    @property
    def net_cash_flow(self) -> float:
        return round(self.cash_in_total - self.cash_out_total, 2)


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _forecast_sales_by_month(db: Session, company_id, periods: int) -> dict:
    """Sum an exponential-smoothing sales forecast across every product with
    history, bucketed by the calendar month each forecast point lands in."""
    totals: dict = defaultdict(float)
    products = db.query(Product).filter(Product.company_id == company_id).all()

    for product in products:
        actuals = (
            db.query(SalesActual)
            .filter(SalesActual.company_id == company_id, SalesActual.product_id == product.id)
            .order_by(SalesActual.period)
            .all()
        )
        if not actuals:
            continue

        history = pd.Series([float(a.amount) for a in actuals], index=[a.period for a in actuals])
        points = forecasting.forecast(history, model="exponential_smoothing", periods=periods)
        last_period = actuals[-1].period
        for point in points:
            cal_period = _month_start(last_period + relativedelta(months=point.period_offset))
            totals[cal_period] += point.forecast

    return totals


def _approved_budget_outflows_by_month(db: Session, company_id) -> dict:
    totals: dict = defaultdict(float)
    rows = (
        db.query(BudgetLine)
        .join(Budget, Budget.id == BudgetLine.budget_id)
        .filter(Budget.company_id == company_id, Budget.type == "expense", Budget.status == "approved")
        .all()
    )
    for line in rows:
        totals[_month_start(line.period)] += float(line.amount)
    return totals


def _manual_items_by_month(db: Session, company_id) -> tuple:
    cash_in: dict = defaultdict(float)
    cash_out: dict = defaultdict(float)
    items = db.query(CashItem).filter(CashItem.company_id == company_id).all()
    for item in items:
        bucket = cash_in if item.direction == "in" else cash_out
        bucket[_month_start(item.period)] += float(item.amount)
    return cash_in, cash_out


def build_forecast(
    db: Session,
    company_id,
    start_period: date,
    periods: int = 12,
    collection_lag_days: int = 30,
    opening_balance: float = 0.0,
) -> list:
    start_period = _month_start(start_period)
    target_months = [start_period + relativedelta(months=i) for i in range(periods)]

    sales_by_month = _forecast_sales_by_month(db, company_id, periods)
    lag_months = round(collection_lag_days / 30)
    collections_by_month: dict = defaultdict(float)
    for month, amount in sales_by_month.items():
        collections_by_month[_month_start(month + relativedelta(months=lag_months))] += amount

    budget_outflows = _approved_budget_outflows_by_month(db, company_id)
    manual_in, manual_out = _manual_items_by_month(db, company_id)

    result: list = []
    running_balance = opening_balance
    for month in target_months:
        row = CashFlowPeriod(
            period=month,
            cash_in_forecast=round(collections_by_month.get(month, 0.0), 2),
            cash_in_manual=round(manual_in.get(month, 0.0), 2),
            cash_out_budget=round(budget_outflows.get(month, 0.0), 2),
            cash_out_manual=round(manual_out.get(month, 0.0), 2),
            opening_balance=round(running_balance, 2),
        )
        running_balance += row.net_cash_flow
        row.closing_balance = round(running_balance, 2)
        result.append(row)

    return result
