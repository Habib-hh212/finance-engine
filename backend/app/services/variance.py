"""Budget vs. actual variance and budget-consumption tracking with
traffic-light status (green / yellow / red).

Variance direction matters: for an EXPENSE account, spending *more* than
budgeted is unfavorable; for a REVENUE account, earning *less* than
budgeted is unfavorable. The thresholds below are on the unfavorable
side only — favorable variances (underspend, overachievement) are
always green regardless of size.

Budget-vs-actual compares only APPROVED budgets against actuals — an
unapproved budget isn't a commitment yet, consistent with the Cash
Flow Forecast module. Budget *consumption* tracking (spent vs.
remaining) intentionally does NOT require approval, since department
managers watch spend against a working budget throughout the approval
cycle, not only after CFO sign-off.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ActualLine, Budget, BudgetLine, GLAccount

VARIANCE_YELLOW_PCT = 5.0
VARIANCE_RED_PCT = 15.0

CONSUMPTION_YELLOW_PCT = 80.0
CONSUMPTION_RED_PCT = 100.0


def _status_for_unfavorable_pct(unfavorable_pct: float) -> str:
    if unfavorable_pct >= VARIANCE_RED_PCT:
        return "red"
    if unfavorable_pct >= VARIANCE_YELLOW_PCT:
        return "yellow"
    return "green"


@dataclass
class VarianceRow:
    gl_account_id: object
    gl_account_code: str
    gl_account_name: str
    category: str
    period: date
    budget_amount: float
    actual_amount: float
    variance_amount: float
    variance_pct: Optional[float]
    status: str


def budget_vs_actual(db: Session, company_id, fiscal_year: Optional[int] = None) -> list:
    budget_query = db.query(Budget).filter(Budget.company_id == company_id, Budget.status == "approved")
    if fiscal_year is not None:
        budget_query = budget_query.filter(Budget.fiscal_year == fiscal_year)
    approved_budget_ids = [b.id for b in budget_query.all()]

    budget_totals: dict = defaultdict(float)
    if approved_budget_ids:
        lines = db.query(BudgetLine).filter(BudgetLine.budget_id.in_(approved_budget_ids)).all()
        for line in lines:
            budget_totals[(line.gl_account_id, line.period)] += float(line.amount)

    actual_totals: dict = defaultdict(float)
    gl_accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    actuals = db.query(ActualLine).filter(ActualLine.company_id == company_id).all()
    for line in actuals:
        actual_totals[(line.gl_account_id, line.period)] += float(line.amount)

    keys = set(budget_totals) | set(actual_totals)
    rows = []
    for gl_account_id, period in sorted(keys, key=lambda k: (str(k[0]), k[1])):
        account = gl_accounts.get(gl_account_id)
        if account is None:
            continue  # actual posted against a GL account outside this company; skip defensively
        budget_amount = round(budget_totals.get((gl_account_id, period), 0.0), 2)
        actual_amount = round(actual_totals.get((gl_account_id, period), 0.0), 2)
        variance_amount = round(actual_amount - budget_amount, 2)

        if budget_amount == 0:
            variance_pct = None
            status = "green" if actual_amount == 0 else "red"
        else:
            variance_pct = round((variance_amount / budget_amount) * 100, 1)
            if account.category == "expense":
                unfavorable_pct = variance_pct  # spending more than budget is unfavorable
            else:
                unfavorable_pct = -variance_pct  # earning less than budget is unfavorable
            status = _status_for_unfavorable_pct(unfavorable_pct)

        rows.append(
            VarianceRow(
                gl_account_id=gl_account_id,
                gl_account_code=account.code,
                gl_account_name=account.name,
                category=account.category,
                period=period,
                budget_amount=budget_amount,
                actual_amount=actual_amount,
                variance_amount=variance_amount,
                variance_pct=variance_pct,
                status=status,
            )
        )
    return rows


@dataclass
class BudgetConsumption:
    budget_id: object
    budget_amount: float
    spent: float
    remaining: float
    consumption_pct: Optional[float]
    status: str


def budget_consumption(db: Session, budget: Budget) -> BudgetConsumption:
    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget.id).all()
    budget_amount = round(sum(float(line.amount) for line in lines), 2)
    gl_account_ids = {line.gl_account_id for line in lines}

    spent = 0.0
    if gl_account_ids:
        actuals = (
            db.query(ActualLine)
            .filter(ActualLine.company_id == budget.company_id, ActualLine.gl_account_id.in_(gl_account_ids))
            .all()
        )
        spent = sum(float(a.amount) for a in actuals)
    spent = round(spent, 2)

    remaining = round(budget_amount - spent, 2)
    if budget_amount == 0:
        consumption_pct = None
        status = "green" if spent == 0 else "red"
    else:
        consumption_pct = round((spent / budget_amount) * 100, 1)
        if consumption_pct >= CONSUMPTION_RED_PCT:
            status = "red"
        elif consumption_pct >= CONSUMPTION_YELLOW_PCT:
            status = "yellow"
        else:
            status = "green"

    return BudgetConsumption(
        budget_id=budget.id,
        budget_amount=budget_amount,
        spent=spent,
        remaining=remaining,
        consumption_pct=consumption_pct,
        status=status,
    )


@dataclass
class FlexibleVarianceRow:
    """Flexible-budget variance decomposes the total variance into two parts:

    - spending variance: actual cost vs. what the budget WOULD have allowed
      at the actual activity level (the flexed budget) -- this isolates
      whether managers spent efficiently.
    - volume variance: the flexed budget vs. the original static budget --
      this isolates the effect of activity being higher/lower than planned,
      which isn't a manager's spending decision.
    """

    gl_account_id: object
    gl_account_code: str
    gl_account_name: str
    period: date
    static_amount: float
    variable_rate_per_unit: float
    actual_quantity: Optional[float]
    flexed_amount: float
    actual_amount: float
    spending_variance: float
    volume_variance: float
    total_variance: float


def flexible_budget_variance(db: Session, budget: Budget) -> list[FlexibleVarianceRow]:
    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget.id).all()
    gl_accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == budget.company_id).all()}

    actuals = (
        db.query(ActualLine)
        .filter(ActualLine.company_id == budget.company_id, ActualLine.gl_account_id.in_({line.gl_account_id for line in lines}))
        .all()
        if lines
        else []
    )
    actual_amount_totals: dict = defaultdict(float)
    actual_qty_totals: dict = defaultdict(float)
    for actual in actuals:
        key = (actual.gl_account_id, actual.period)
        actual_amount_totals[key] += float(actual.amount)
        actual_qty_totals[key] += float(actual.actual_quantity or 0.0)

    rows = []
    for line in lines:
        account = gl_accounts.get(line.gl_account_id)
        if account is None:
            continue

        key = (line.gl_account_id, line.period)
        static_amount = round(float(line.amount), 2)
        variable_rate = float(line.variable_rate_per_unit or 0.0)
        actual_quantity = actual_qty_totals.get(key)
        flexed_amount = round(static_amount + variable_rate * (actual_quantity or 0.0), 2)
        actual_amount = round(actual_amount_totals.get(key, 0.0), 2)

        rows.append(
            FlexibleVarianceRow(
                gl_account_id=line.gl_account_id,
                gl_account_code=account.code,
                gl_account_name=account.name,
                period=line.period,
                static_amount=static_amount,
                variable_rate_per_unit=variable_rate,
                actual_quantity=actual_quantity,
                flexed_amount=flexed_amount,
                actual_amount=actual_amount,
                spending_variance=round(actual_amount - flexed_amount, 2),
                volume_variance=round(flexed_amount - static_amount, 2),
                total_variance=round(actual_amount - static_amount, 2),
            )
        )
    return rows
