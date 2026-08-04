"""Real currency conversion -- the first actual use of `ExchangeRate`
anywhere in this codebase. Every other module (Cash Flow Forecast,
Financial Statements, KPIs, ...) sums `amount` fields as if they were
already in the company's base currency; `currency` on those rows has been
metadata only, with real conversion explicitly deferred (see
`cashflow.py`'s docstring). This module doesn't retrofit conversion into
every aggregation -- that's a wider, riskier change than "add FX" should
be -- it backs the new FX Scenario tool (`fx_scenario.py`), which is where
real conversion first gets used for something.
"""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ExchangeRate


def latest_rate(db: Session, from_currency: str, to_currency: str, as_of: date) -> Optional[float]:
    """The most recent rate on file on or before `as_of` -- never a future
    rate, and never invented when none exists (returns None rather than
    assuming 1:1)."""
    if from_currency == to_currency:
        return 1.0
    row = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
            ExchangeRate.rate_date <= as_of,
        )
        .order_by(ExchangeRate.rate_date.desc())
        .first()
    )
    return float(row.rate) if row is not None else None
