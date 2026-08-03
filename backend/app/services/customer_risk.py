"""Customer churn risk: a statistical recency/frequency score, not a
trained classifier.

There's no ground-truth "did this customer churn" label anywhere in this
system -- no subscription end dates, no cancellation events, nothing. A
classifier "trained" to predict churn here would really be trained on a
label invented for the occasion, which isn't machine learning so much as
ML costume on a guess. This computes something narrower but honest
instead: how much longer it's been since a customer's last order than
their *own* typical gap between orders, as a ratio. A customer who
usually orders every ~2 months and hasn't in 5 is a real, defensible risk
signal; a customer who always orders once a year and it's been 8 months
is not -- a fixed "no order in N months" rule would get both wrong.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Customer, SalesActual

MIN_DISTINCT_ORDER_MONTHS = 2
HIGH_RISK_RATIO = 2.0
MEDIUM_RISK_RATIO = 1.3


@dataclass
class CustomerChurnRisk:
    customer_id: object
    name: str
    last_order_period: date
    months_since_last_order: int
    avg_order_interval_months: float
    risk_ratio: float
    risk_level: str  # low | medium | high
    total_revenue: float


def _month_diff(later: date, earlier: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def compute_churn_risk(db: Session, company_id, as_of: Optional[date] = None) -> list[CustomerChurnRisk]:
    as_of = as_of or date.today()
    customers = db.query(Customer).filter(Customer.company_id == company_id).all()

    results = []
    for customer in customers:
        actuals = (
            db.query(SalesActual)
            .filter(SalesActual.company_id == company_id, SalesActual.customer_id == customer.id)
            .order_by(SalesActual.period)
            .all()
        )
        if not actuals:
            continue

        order_months = sorted({a.period for a in actuals})
        total_revenue = round(sum(float(a.amount) for a in actuals), 2)
        if len(order_months) < MIN_DISTINCT_ORDER_MONTHS:
            continue  # a single order establishes no cadence to compare against

        gaps = [_month_diff(order_months[i], order_months[i - 1]) for i in range(1, len(order_months))]
        avg_interval = sum(gaps) / len(gaps)
        if avg_interval <= 0:
            continue  # every order landed in the same calendar month; no gap to measure

        last_order = order_months[-1]
        months_since = _month_diff(as_of, last_order)
        risk_ratio = round(months_since / avg_interval, 2)

        if risk_ratio >= HIGH_RISK_RATIO:
            risk_level = "high"
        elif risk_ratio >= MEDIUM_RISK_RATIO:
            risk_level = "medium"
        else:
            risk_level = "low"

        results.append(
            CustomerChurnRisk(
                customer_id=customer.id,
                name=customer.name,
                last_order_period=last_order,
                months_since_last_order=months_since,
                avg_order_interval_months=round(avg_interval, 1),
                risk_ratio=risk_ratio,
                risk_level=risk_level,
                total_revenue=total_revenue,
            )
        )

    risk_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(results, key=lambda r: (risk_rank[r.risk_level], -r.risk_ratio))
