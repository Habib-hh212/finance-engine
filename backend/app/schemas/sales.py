import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class SalesUploadResult(BaseModel):
    rows_imported: int
    products_created: int
    customers_created: int


class ForecastPointOut(BaseModel):
    period: date
    forecast: float
    lower_bound: float
    upper_bound: float
    currency: str


class ForecastResponse(BaseModel):
    company_id: uuid.UUID
    product_id: uuid.UUID
    model: str
    history_periods: int
    points: list[ForecastPointOut]


class ModelComparisonOut(BaseModel):
    company_id: uuid.UUID
    product_id: uuid.UUID
    history_periods: int
    mape_by_model: dict[str, Optional[float]]


class DemandForecastPointOut(BaseModel):
    period: date
    forecast_units: float
    lower_bound: float
    upper_bound: float


class DemandForecastResponse(BaseModel):
    company_id: uuid.UUID
    product_id: uuid.UUID
    model: str
    history_periods: int
    points: list[DemandForecastPointOut]


class MonteCarloPointOut(BaseModel):
    period: date
    p10: float
    p50: float
    p90: float
    mean: float
    currency: str


class MonteCarloResponse(BaseModel):
    company_id: uuid.UUID
    product_id: uuid.UUID
    model: str
    trials: int
    history_periods: int
    points: list[MonteCarloPointOut]


class CompanyCreate(BaseModel):
    name: str
    base_currency: str = "USD"


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    base_currency: str

    model_config = {"from_attributes": True}
