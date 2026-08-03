import uuid
from datetime import date

from pydantic import BaseModel


class StandardCostIn(BaseModel):
    product_id: uuid.UUID
    material_std_price: float
    material_std_qty: float
    labor_std_rate: float
    labor_std_hours: float
    variable_overhead_std_rate: float
    fixed_overhead_std_rate: float
    fixed_overhead_budgeted: float


class StandardCostOut(StandardCostIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ProductionActualIn(BaseModel):
    product_id: uuid.UUID
    period: date
    units_produced: float
    material_actual_price: float
    material_actual_qty: float
    labor_actual_rate: float
    labor_actual_hours: float
    actual_variable_overhead: float
    actual_fixed_overhead: float


class ProductionActualOut(ProductionActualIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class StandardCostVarianceOut(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    period: date

    material_price_variance: float
    material_quantity_variance: float
    material_total_variance: float

    labor_rate_variance: float
    labor_efficiency_variance: float
    labor_total_variance: float

    variable_overhead_spending_variance: float
    variable_overhead_efficiency_variance: float
    variable_overhead_total_variance: float

    fixed_overhead_budget_variance: float
    fixed_overhead_volume_variance: float
    fixed_overhead_total_variance: float

    total_cost_variance: float
