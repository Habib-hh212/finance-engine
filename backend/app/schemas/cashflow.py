import uuid
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

CashCategory = Literal["receivable_collection", "payroll", "vendor_payment", "tax", "loan", "interest", "other"]


class CashItemCreate(BaseModel):
    category: CashCategory
    direction: Literal["in", "out"]
    period: date
    amount: float
    currency: str = "USD"
    description: Optional[str] = None


class CashItemOut(BaseModel):
    id: uuid.UUID
    category: str
    direction: str
    period: date
    amount: float
    currency: str
    description: Optional[str]

    model_config = {"from_attributes": True}


class CashFlowPeriodOut(BaseModel):
    period: date
    cash_in_forecast: float
    cash_in_manual: float
    cash_in_total: float
    cash_out_budget: float
    cash_out_manual: float
    cash_out_total: float
    net_cash_flow: float
    opening_balance: float
    closing_balance: float


class CashFlowForecastResponse(BaseModel):
    company_id: uuid.UUID
    start_period: date
    periods: int
    collection_lag_days: int
    rows: list[CashFlowPeriodOut]
