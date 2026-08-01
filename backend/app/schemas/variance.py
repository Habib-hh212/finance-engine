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
