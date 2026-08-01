import uuid
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
