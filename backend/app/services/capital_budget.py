"""Capital budgeting appraisal: payback period and simple ROI per line.

Each capital budget line represents one investment: `amount` is the initial
outlay, `annual_cash_flow` is the expected return per year, and
`useful_life_years` is how long that return is expected to last. Appraisal
is intentionally simple (no discounting/NPV/IRR) -- consistent with the
rest of Phase 2 favoring straightforward, explainable formulas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetLine, GLAccount


@dataclass
class CapitalAppraisalRow:
    gl_account_id: object
    gl_account_code: str
    gl_account_name: str
    period: date
    investment: float
    annual_cash_flow: Optional[float]
    useful_life_years: Optional[int]
    payback_period_years: Optional[float]
    total_cash_flow: Optional[float]
    net_gain: Optional[float]
    roi_pct: Optional[float]
    average_annual_roi_pct: Optional[float]


def capital_appraisal(db: Session, budget: Budget) -> list[CapitalAppraisalRow]:
    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget.id).all()
    gl_accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == budget.company_id).all()}

    rows = []
    for line in lines:
        account = gl_accounts.get(line.gl_account_id)
        if account is None:
            continue

        investment = round(float(line.amount), 2)
        annual_cash_flow = float(line.annual_cash_flow) if line.annual_cash_flow is not None else None
        useful_life_years = line.useful_life_years

        payback_period_years = None
        total_cash_flow = None
        net_gain = None
        roi_pct = None
        average_annual_roi_pct = None

        if annual_cash_flow is not None:
            average_annual_roi_pct = round((annual_cash_flow / investment) * 100, 1) if investment else None
            if annual_cash_flow > 0:
                payback_period_years = round(investment / annual_cash_flow, 2)
            if useful_life_years is not None:
                total_cash_flow = round(annual_cash_flow * useful_life_years, 2)
                net_gain = round(total_cash_flow - investment, 2)
                roi_pct = round((net_gain / investment) * 100, 1) if investment else None

        rows.append(
            CapitalAppraisalRow(
                gl_account_id=line.gl_account_id,
                gl_account_code=account.code,
                gl_account_name=account.name,
                period=line.period,
                investment=investment,
                annual_cash_flow=annual_cash_flow,
                useful_life_years=useful_life_years,
                payback_period_years=payback_period_years,
                total_cash_flow=total_cash_flow,
                net_gain=net_gain,
                roi_pct=roi_pct,
                average_annual_roi_pct=average_annual_roi_pct,
            )
        )
    return rows
