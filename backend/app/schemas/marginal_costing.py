import uuid
from typing import Optional

from pydantic import BaseModel


class FixedCostIn(BaseModel):
    fiscal_year: int
    name: str
    amount: float
    currency: str = "USD"
    category: Optional[str] = None


class FixedCostOut(FixedCostIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class MarginalCostingSummaryOut(BaseModel):
    fiscal_year: int
    revenue: float
    variable_cost: float
    contribution_margin: float
    contribution_margin_ratio: Optional[float]
    fixed_costs: float
    net_operating_income: float
    break_even_revenue: Optional[float]
    margin_of_safety: Optional[float]
    margin_of_safety_pct: Optional[float]
    degree_of_operating_leverage: Optional[float]
    uncosted_product_skus: list[str]
