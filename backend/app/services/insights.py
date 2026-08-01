"""AI Recommendation Engine v0: rule-based, not ML.

Reads the outputs of the three modules already built (variance, budget
consumption, sales forecasting) and turns the ones worth a human's
attention into plain-language flags. This mirrors the roadmap's Module 11
examples ("Manufacturing overhead exceeded budget by 18%") using data this
Phase 1 slice actually has. A statistical/NLP version is a Phase 3 item —
this one is closer to a set of named thresholds than intelligence.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Product, SalesActual
from app.services import forecasting, variance

FORECAST_DECLINE_WATCH_PCT = 10.0
FORECAST_DECLINE_ACTION_PCT = 20.0


@dataclass
class Insight:
    type: str
    severity: str  # yellow | red
    message: str


def _budget_variance_insights(db: Session, company_id, fiscal_year: Optional[int]) -> list:
    insights = []
    for row in variance.budget_vs_actual(db, company_id, fiscal_year=fiscal_year):
        period_label = row.period.strftime("%B %Y")

        if row.budget_amount == 0 and row.actual_amount != 0:
            insights.append(
                Insight(
                    type="unbudgeted_spend",
                    severity="red",
                    message=f"Unbudgeted amount of {row.actual_amount:,.2f} posted to {row.gl_account_name} in {period_label} — no approved budget exists for this account/period.",
                )
            )
            continue

        if row.status == "green" or row.variance_pct is None:
            continue

        if row.category == "expense":
            insights.append(
                Insight(
                    type="budget_overrun",
                    severity=row.status,
                    message=f"{row.gl_account_name} overspent budget by {abs(row.variance_pct):.0f}% in {period_label} ({row.actual_amount:,.2f} vs. {row.budget_amount:,.2f} budgeted).",
                )
            )
        else:
            insights.append(
                Insight(
                    type="revenue_shortfall",
                    severity=row.status,
                    message=f"{row.gl_account_name} revenue missed budget by {abs(row.variance_pct):.0f}% in {period_label} ({row.actual_amount:,.2f} vs. {row.budget_amount:,.2f} budgeted).",
                )
            )
    return insights


def _budget_consumption_insights(db: Session, company_id, fiscal_year: Optional[int]) -> list:
    from app.models import Budget  # local import to avoid a cycle with variance module

    insights = []
    query = db.query(Budget).filter(Budget.company_id == company_id, Budget.status == "approved")
    if fiscal_year is not None:
        query = query.filter(Budget.fiscal_year == fiscal_year)

    for budget in query.all():
        consumption = variance.budget_consumption(db, budget)
        if consumption.status == "green" or consumption.consumption_pct is None:
            continue
        insights.append(
            Insight(
                type="budget_consumption",
                severity=consumption.status,
                message=f"{budget.name} is {consumption.consumption_pct:.0f}% consumed ({consumption.spent:,.2f} of {consumption.budget_amount:,.2f}).",
            )
        )
    return insights


def _forecast_decline_insights(db: Session, company_id) -> list:
    insights = []
    products = db.query(Product).filter(Product.company_id == company_id).all()

    for product in products:
        actuals = (
            db.query(SalesActual)
            .filter(SalesActual.company_id == company_id, SalesActual.product_id == product.id)
            .order_by(SalesActual.period)
            .all()
        )
        if len(actuals) < 2:
            continue

        history = pd.Series([float(a.amount) for a in actuals], index=[a.period for a in actuals])
        last_actual = float(actuals[-1].amount)
        if last_actual == 0:
            continue

        forecast_point = forecasting.forecast(history, model="exponential_smoothing", periods=1)[0]
        pct_change = ((forecast_point.forecast - last_actual) / last_actual) * 100

        if pct_change <= -FORECAST_DECLINE_ACTION_PCT:
            severity = "red"
        elif pct_change <= -FORECAST_DECLINE_WATCH_PCT:
            severity = "yellow"
        else:
            continue

        insights.append(
            Insight(
                type="forecast_decline",
                severity=severity,
                message=f"{product.name} sales are forecasted to decline {abs(pct_change):.0f}% next month.",
            )
        )
    return insights


def generate_insights(db: Session, company_id, fiscal_year: Optional[int] = None) -> list:
    insights = (
        _budget_variance_insights(db, company_id, fiscal_year)
        + _budget_consumption_insights(db, company_id, fiscal_year)
        + _forecast_decline_insights(db, company_id)
    )
    severity_rank = {"red": 0, "yellow": 1}
    return sorted(insights, key=lambda i: severity_rank[i.severity])
