"""Standard costing variance analysis -- the classic 8-variance method
(material price/quantity, labor rate/efficiency, variable overhead
spending/efficiency, fixed overhead budget/volume).

Sign convention throughout: positive = favorable (actual cost came in
under standard), negative = unfavorable. This matches the textbook
formulas below directly -- no separate favorable/unfavorable flag needed,
the sign already says it.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Product, ProductionActual, StandardCost


@dataclass
class StandardCostVariance:
    product_id: object
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


def _compute(product: Product, std: StandardCost, actual: ProductionActual) -> StandardCostVariance:
    std_qty_allowed = float(actual.units_produced) * float(std.material_std_qty)
    std_hours_allowed = float(actual.units_produced) * float(std.labor_std_hours)

    material_price_variance = round(
        (float(std.material_std_price) - float(actual.material_actual_price)) * float(actual.material_actual_qty), 2
    )
    material_quantity_variance = round(
        (std_qty_allowed - float(actual.material_actual_qty)) * float(std.material_std_price), 2
    )

    labor_rate_variance = round(
        (float(std.labor_std_rate) - float(actual.labor_actual_rate)) * float(actual.labor_actual_hours), 2
    )
    labor_efficiency_variance = round((std_hours_allowed - float(actual.labor_actual_hours)) * float(std.labor_std_rate), 2)

    voh_spending_variance = round(
        float(std.variable_overhead_std_rate) * float(actual.labor_actual_hours) - float(actual.actual_variable_overhead), 2
    )
    voh_efficiency_variance = round(
        (std_hours_allowed - float(actual.labor_actual_hours)) * float(std.variable_overhead_std_rate), 2
    )

    foh_budget_variance = round(float(std.fixed_overhead_budgeted) - float(actual.actual_fixed_overhead), 2)
    foh_volume_variance = round(
        std_hours_allowed * float(std.fixed_overhead_std_rate) - float(std.fixed_overhead_budgeted), 2
    )

    material_total = round(material_price_variance + material_quantity_variance, 2)
    labor_total = round(labor_rate_variance + labor_efficiency_variance, 2)
    voh_total = round(voh_spending_variance + voh_efficiency_variance, 2)
    foh_total = round(foh_budget_variance + foh_volume_variance, 2)

    return StandardCostVariance(
        product_id=product.id,
        product_sku=product.sku,
        product_name=product.name,
        period=actual.period,
        material_price_variance=material_price_variance,
        material_quantity_variance=material_quantity_variance,
        material_total_variance=material_total,
        labor_rate_variance=labor_rate_variance,
        labor_efficiency_variance=labor_efficiency_variance,
        labor_total_variance=labor_total,
        variable_overhead_spending_variance=voh_spending_variance,
        variable_overhead_efficiency_variance=voh_efficiency_variance,
        variable_overhead_total_variance=voh_total,
        fixed_overhead_budget_variance=foh_budget_variance,
        fixed_overhead_volume_variance=foh_volume_variance,
        fixed_overhead_total_variance=foh_total,
        total_cost_variance=round(material_total + labor_total + voh_total + foh_total, 2),
    )


def variance_for_company(db: Session, company_id, fiscal_year: Optional[int] = None) -> list[StandardCostVariance]:
    products = {p.id: p for p in db.query(Product).filter(Product.company_id == company_id).all()}
    standards = {
        s.product_id: s for s in db.query(StandardCost).filter(StandardCost.company_id == company_id).all()
    }
    actuals_query = db.query(ProductionActual).filter(ProductionActual.company_id == company_id)
    if fiscal_year is not None:
        actuals_query = actuals_query.filter(
            ProductionActual.period >= date(fiscal_year, 1, 1), ProductionActual.period <= date(fiscal_year, 12, 31)
        )

    rows = []
    for actual in actuals_query.order_by(ProductionActual.period).all():
        product = products.get(actual.product_id)
        std = standards.get(actual.product_id)
        if product is None or std is None:
            continue  # no standard cost set for this product yet -- nothing to compare against
        rows.append(_compute(product, std, actual))
    return rows
