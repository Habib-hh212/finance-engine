"""FX Scenario: the currency-risk counterpart to Scenario Planning's
sales/expense growth what-ifs. Converts a company's non-base-currency sales
actuals into base currency using the latest known rate as of each period,
then shows what the same native-currency total would be worth if that rate
moved by a hypothetical shock percentage -- how much of the company's
reported revenue is currency risk versus real business performance.

Scoped to sales actuals (the clearest, most common FX exposure: revenue
booked in a foreign currency). GL actuals also carry a `currency` field and
would be a natural next extension, but folding both in at once risked a
sprawling change; this ships the real, working piece rather than a wider
half-finished one.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Company, SalesActual
from app.services import fx


@dataclass
class FxExposureLine:
    currency: str
    period: date
    native_amount: float
    rate_used: Optional[float]
    base_amount: Optional[float]


@dataclass
class FxScenarioResult:
    base_currency: str
    shock_pct: float
    lines: list[FxExposureLine]
    total_base_actual: float
    total_base_shocked: float
    impact: float
    unrated_currencies: list[str]


def compute_fx_exposure(db: Session, company_id, start_period: date, end_period: date) -> list[FxExposureLine]:
    company = db.get(Company, company_id)
    base_currency = company.base_currency if company is not None else "USD"

    actuals = (
        db.query(SalesActual)
        .filter(
            SalesActual.company_id == company_id,
            SalesActual.period >= start_period,
            SalesActual.period <= end_period,
            SalesActual.currency != base_currency,
        )
        .order_by(SalesActual.period)
        .all()
    )

    lines = []
    for actual in actuals:
        rate = fx.latest_rate(db, actual.currency, base_currency, actual.period)
        native_amount = float(actual.amount)
        base_amount = round(native_amount * rate, 2) if rate is not None else None
        lines.append(FxExposureLine(currency=actual.currency, period=actual.period, native_amount=native_amount, rate_used=rate, base_amount=base_amount))
    return lines


def simulate_fx_scenario(db: Session, company_id, start_period: date, end_period: date, shock_pct: float) -> FxScenarioResult:
    company = db.get(Company, company_id)
    base_currency = company.base_currency if company is not None else "USD"
    lines = compute_fx_exposure(db, company_id, start_period, end_period)

    total_actual = round(sum(line.base_amount for line in lines if line.base_amount is not None), 2)
    total_shocked = round(
        sum(line.native_amount * line.rate_used * (1 + shock_pct / 100) for line in lines if line.rate_used is not None), 2
    )
    unrated = sorted({line.currency for line in lines if line.rate_used is None})

    return FxScenarioResult(
        base_currency=base_currency,
        shock_pct=shock_pct,
        lines=lines,
        total_base_actual=total_actual,
        total_base_shocked=total_shocked,
        impact=round(total_shocked - total_actual, 2),
        unrated_currencies=unrated,
    )
