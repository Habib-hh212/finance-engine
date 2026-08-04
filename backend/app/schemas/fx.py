import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class ExchangeRateCreate(BaseModel):
    from_currency: str
    to_currency: str
    rate_date: date
    rate: float


class ExchangeRateOut(BaseModel):
    id: uuid.UUID
    from_currency: str
    to_currency: str
    rate_date: date
    rate: float

    model_config = {"from_attributes": True}


class FxExposureLineOut(BaseModel):
    currency: str
    period: date
    native_amount: float
    rate_used: Optional[float]
    base_amount: Optional[float]

    model_config = {"from_attributes": True}


class FxScenarioOut(BaseModel):
    base_currency: str
    shock_pct: float
    lines: list[FxExposureLineOut]
    total_base_actual: float
    total_base_shocked: float
    impact: float
    unrated_currencies: list[str]
