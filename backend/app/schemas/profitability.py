import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class ProductProfitabilityOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    quantity: float
    revenue: float
    unit_price: Optional[float]
    unit_variable_cost: Optional[float]
    contribution_per_unit: Optional[float]
    contribution_margin_total: Optional[float]
    contribution_margin_pct: Optional[float]


class CustomerProfitabilityOut(BaseModel):
    customer_id: uuid.UUID
    name: str
    revenue: float
    contribution_margin_total: Optional[float]
    contribution_margin_pct: Optional[float]


class CustomerChurnRiskOut(BaseModel):
    customer_id: uuid.UUID
    name: str
    last_order_period: date
    months_since_last_order: int
    avg_order_interval_months: float
    risk_ratio: float
    risk_level: str
    total_revenue: float
