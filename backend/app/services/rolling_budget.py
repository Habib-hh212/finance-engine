"""Rolling budget roll-forward.

A rolling budget always covers a fixed-size forward window
(`rolling_window_months`, e.g. 12 months). Rolling forward adds one new
period -- copying the most recent period's lines as the starting point for
the new one -- and drops the oldest period, so the window stays a constant
size instead of growing every time.
"""
from __future__ import annotations

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetLine, BudgetStatus


class RollForwardError(ValueError):
    """Raised when a roll-forward isn't valid for this budget."""


def roll_forward(db: Session, budget: Budget) -> Budget:
    if budget.type != "rolling":
        raise RollForwardError("Only rolling budgets support roll-forward")
    if budget.status != BudgetStatus.DRAFT:
        raise RollForwardError("Roll-forward is only allowed while the budget is in 'draft'")

    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget.id).all()
    if not lines:
        raise RollForwardError("Budget has no lines to roll forward from")

    window = budget.rolling_window_months or 12
    periods = sorted({line.period for line in lines})
    latest_period = periods[-1]
    new_period = latest_period + relativedelta(months=1)

    for line in lines:
        if line.period == latest_period:
            db.add(
                BudgetLine(
                    budget_id=budget.id,
                    gl_account_id=line.gl_account_id,
                    period=new_period,
                    amount=line.amount,
                    currency=line.currency,
                    justification=line.justification,
                    variable_rate_per_unit=line.variable_rate_per_unit,
                    useful_life_years=line.useful_life_years,
                    annual_cash_flow=line.annual_cash_flow,
                )
            )

    all_periods = sorted(set(periods) | {new_period})
    if len(all_periods) > window:
        periods_to_drop = set(all_periods[: len(all_periods) - window])
        db.query(BudgetLine).filter(
            BudgetLine.budget_id == budget.id, BudgetLine.period.in_(periods_to_drop)
        ).delete(synchronize_session=False)

    db.commit()
    db.refresh(budget)
    return budget
