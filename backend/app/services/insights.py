"""AI Recommendation Engine: rule-based flags (Phase 1) plus statistical
anomaly detection (Phase 3) -- deliberately still not ML/NLP. A "spike" or
"drop" here is a z-score against an account's/product's own history, not a
model trained on labeled outcomes; this system has no such labels to train
on. That's a real limitation worth being upfront about, not a step toward
faking intelligence it doesn't have.

The rule-based flags (budget variance, budget consumption, next-month
forecast decline) use fixed thresholds uniformly across every account --
useful, but blind to whether a given account is normally volatile or
normally stable. The anomaly detectors below complement that: they flag
whatever is unusual *for that specific account or product*, so a naturally
noisy account crossing a fixed threshold isn't over-flagged, and a normally
stable one moving by a smaller amount than the fixed threshold, but still
far outside its own norm, isn't missed.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import ActualLine, GLAccount, Product, SalesActual
from app.services import forecasting, variance

FORECAST_DECLINE_WATCH_PCT = 10.0
FORECAST_DECLINE_ACTION_PCT = 20.0

ANOMALY_Z_YELLOW = 2.0
ANOMALY_Z_RED = 3.0
MIN_ANOMALY_HISTORY = 4


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


def _latest_period_zscore(amounts: list[float]) -> Optional[tuple[float, float]]:
    """Z-score of the most recent value against the mean/std of everything
    before it -- population std (divide by n, not n-1), since this describes
    the account/product's own observed history rather than sampling a wider
    population. Returns (z, mean) or None if there's not enough history or
    the history has zero variance (a z-score against no spread is undefined,
    not "extreme")."""
    if len(amounts) < MIN_ANOMALY_HISTORY + 1:
        return None
    history = amounts[:-1]
    latest = amounts[-1]
    mean = sum(history) / len(history)
    variance_ = sum((x - mean) ** 2 for x in history) / len(history)
    std = variance_**0.5
    if std == 0:
        return None
    return (latest - mean) / std, mean


def _severity_for_z(z: float) -> Optional[str]:
    if abs(z) >= ANOMALY_Z_RED:
        return "red"
    if abs(z) >= ANOMALY_Z_YELLOW:
        return "yellow"
    return None


def _spend_anomaly_insights(db: Session, company_id) -> list:
    insights = []
    accounts = db.query(GLAccount).filter(GLAccount.company_id == company_id).all()

    for account in accounts:
        actuals = (
            db.query(ActualLine)
            .filter(ActualLine.company_id == company_id, ActualLine.gl_account_id == account.id)
            .order_by(ActualLine.period)
            .all()
        )
        result = _latest_period_zscore([float(a.amount) for a in actuals])
        if result is None:
            continue
        z, mean = result
        severity = _severity_for_z(z)
        if severity is None:
            continue

        period_label = actuals[-1].period.strftime("%B %Y")
        direction = "spiked" if z > 0 else "dropped"
        insights.append(
            Insight(
                type="spend_anomaly",
                severity=severity,
                message=f"{account.name} {direction} to {float(actuals[-1].amount):,.2f} in {period_label} — {abs(z):.1f} standard deviations from its usual {mean:,.2f}.",
            )
        )
    return insights


def _sales_anomaly_insights(db: Session, company_id) -> list:
    insights = []
    products = db.query(Product).filter(Product.company_id == company_id).all()

    for product in products:
        actuals = (
            db.query(SalesActual)
            .filter(SalesActual.company_id == company_id, SalesActual.product_id == product.id)
            .order_by(SalesActual.period)
            .all()
        )
        result = _latest_period_zscore([float(a.amount) for a in actuals])
        if result is None:
            continue
        z, mean = result
        severity = _severity_for_z(z)
        if severity is None:
            continue

        period_label = actuals[-1].period.strftime("%B %Y")
        direction = "spiked" if z > 0 else "dropped"
        insights.append(
            Insight(
                type="sales_anomaly",
                severity=severity,
                message=f"{product.name} sales {direction} to {float(actuals[-1].amount):,.2f} in {period_label} — {abs(z):.1f} standard deviations from its usual {mean:,.2f}.",
            )
        )
    return insights


def generate_insights(db: Session, company_id, fiscal_year: Optional[int] = None) -> list:
    insights = (
        _budget_variance_insights(db, company_id, fiscal_year)
        + _budget_consumption_insights(db, company_id, fiscal_year)
        + _forecast_decline_insights(db, company_id)
        + _spend_anomaly_insights(db, company_id)
        + _sales_anomaly_insights(db, company_id)
    )
    severity_rank = {"red": 0, "yellow": 1}
    return sorted(insights, key=lambda i: severity_rank[i.severity])
