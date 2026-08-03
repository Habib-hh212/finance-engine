import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class VarianceRowOut(BaseModel):
    gl_account_id: uuid.UUID
    gl_account_code: str
    gl_account_name: str
    category: str
    period: date
    budget_amount: float
    actual_amount: float
    variance_amount: float
    variance_pct: Optional[float]
    status: str


class BudgetConsumptionOut(BaseModel):
    budget_id: uuid.UUID
    budget_amount: float
    spent: float
    remaining: float
    consumption_pct: Optional[float]
    status: str


class FlexibleVarianceRowOut(BaseModel):
    gl_account_id: uuid.UUID
    gl_account_code: str
    gl_account_name: str
    period: date
    static_amount: float
    variable_rate_per_unit: float
    actual_quantity: Optional[float]
    flexed_amount: float
    actual_amount: float
    spending_variance: float
    volume_variance: float
    total_variance: float


class CapitalAppraisalRowOut(BaseModel):
    gl_account_id: uuid.UUID
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
