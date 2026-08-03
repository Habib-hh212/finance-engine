"""Income Statement and Balance Sheet — built from actuals already in the
system (ActualLine + GLAccount), not a new data source.

Income Statement: revenue actuals minus expense actuals for GL accounts in
that category, over a period range.

Balance Sheet: the running balance of asset/liability/equity GL accounts as
of a date — the sum of every actual posted to that account up to and
including that date. This assumes actuals posted to balance-sheet accounts
represent balance movements (a deposit, a loan draw, etc.), which is a
simplification: there's no double-entry enforcement here, so nothing
guarantees assets == liabilities + equity. The report surfaces whether it
balances rather than assuming it does.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ActualLine, GLAccount

BALANCE_TOLERANCE = 0.01


@dataclass
class AccountAmount:
    gl_account_id: object
    code: str
    name: str
    amount: float


@dataclass
class IncomeStatement:
    start_period: date
    end_period: date
    revenue_lines: list
    total_revenue: float
    expense_lines: list
    total_expense: float
    net_profit: float


@dataclass
class BalanceSheet:
    as_of: date
    asset_lines: list
    total_assets: float
    liability_lines: list
    total_liabilities: float
    equity_lines: list
    total_equity: float
    is_balanced: bool
    difference: float


def _actual_totals_by_account(
    db: Session, company_id, categories: set, period_start: Optional[date] = None, period_end: Optional[date] = None
) -> list:
    accounts = [a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all() if a.category in categories]
    account_by_id = {a.id: a for a in accounts}
    if not accounts:
        return []

    query = db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id.in_(account_by_id.keys()))
    if period_start is not None:
        query = query.filter(ActualLine.period >= period_start)
    if period_end is not None:
        query = query.filter(ActualLine.period <= period_end)

    totals: dict = defaultdict(float)
    for line in query.all():
        totals[line.gl_account_id] += float(line.amount)

    return [
        AccountAmount(gl_account_id=acc_id, code=account_by_id[acc_id].code, name=account_by_id[acc_id].name, amount=round(amount, 2))
        for acc_id, amount in totals.items()
    ]


def monthly_totals_by_category(db: Session, company_id, category: str) -> dict:
    """Every actual posted to accounts in this category, summed by month,
    across the account's *entire* history -- however many years of actuals
    exist, not just a recent window. This is what the historical-trend
    forecast method (see statement_forecast.py) trains on, so someone who's
    bulk-uploaded three or four years of statements gets the full benefit
    of that history rather than a truncated slice.
    """
    account_ids = [
        a.id for a in db.query(GLAccount).filter(GLAccount.company_id == company_id, GLAccount.category == category).all()
    ]
    if not account_ids:
        return {}
    totals: dict = defaultdict(float)
    for line in db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id.in_(account_ids)).all():
        totals[line.period] += float(line.amount)
    return dict(sorted(totals.items()))


def income_statement(db: Session, company_id, start_period: date, end_period: date) -> IncomeStatement:
    revenue_lines = _actual_totals_by_account(db, company_id, {"revenue"}, start_period, end_period)
    expense_lines = _actual_totals_by_account(db, company_id, {"expense"}, start_period, end_period)
    total_revenue = round(sum(line.amount for line in revenue_lines), 2)
    total_expense = round(sum(line.amount for line in expense_lines), 2)
    return IncomeStatement(
        start_period=start_period,
        end_period=end_period,
        revenue_lines=sorted(revenue_lines, key=lambda line: line.code),
        total_revenue=total_revenue,
        expense_lines=sorted(expense_lines, key=lambda line: line.code),
        total_expense=total_expense,
        net_profit=round(total_revenue - total_expense, 2),
    )


@dataclass
class IncomeStatementTrendPoint:
    period: date
    revenue: float
    expense: float
    net_profit: float


def income_statement_trend(db: Session, company_id, start_period: date, end_period: date) -> list:
    """Monthly revenue/expense/net-profit series for the Dashboard's trend
    chart -- the same actuals `income_statement()` totals over a single
    range, but broken out month by month instead of summed into one total.
    """
    revenue_by_month = monthly_totals_by_category(db, company_id, "revenue")
    expense_by_month = monthly_totals_by_category(db, company_id, "expense")
    months = sorted(
        {m for m in revenue_by_month if start_period <= m <= end_period}
        | {m for m in expense_by_month if start_period <= m <= end_period}
    )
    rows = []
    for month in months:
        revenue = round(revenue_by_month.get(month, 0.0), 2)
        expense = round(expense_by_month.get(month, 0.0), 2)
        rows.append(IncomeStatementTrendPoint(period=month, revenue=revenue, expense=expense, net_profit=round(revenue - expense, 2)))
    return rows


def balance_sheet(db: Session, company_id, as_of: date) -> BalanceSheet:
    asset_lines = _actual_totals_by_account(db, company_id, {"asset"}, period_end=as_of)
    liability_lines = _actual_totals_by_account(db, company_id, {"liability"}, period_end=as_of)
    equity_lines = _actual_totals_by_account(db, company_id, {"equity"}, period_end=as_of)

    total_assets = round(sum(line.amount for line in asset_lines), 2)
    total_liabilities = round(sum(line.amount for line in liability_lines), 2)
    total_equity = round(sum(line.amount for line in equity_lines), 2)

    difference = round(total_assets - (total_liabilities + total_equity), 2)

    return BalanceSheet(
        as_of=as_of,
        asset_lines=sorted(asset_lines, key=lambda line: line.code),
        total_assets=total_assets,
        liability_lines=sorted(liability_lines, key=lambda line: line.code),
        total_liabilities=total_liabilities,
        equity_lines=sorted(equity_lines, key=lambda line: line.code),
        total_equity=total_equity,
        is_balanced=abs(difference) <= BALANCE_TOLERANCE,
        difference=difference,
    )
