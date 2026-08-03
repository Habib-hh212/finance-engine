"""Marginal costing / CVP (cost-volume-profit) analysis: break-even revenue,
margin of safety, and degree of operating leverage.

Deliberately company-level, not per-product: fixed costs are period costs
that don't attach to any one unit, so allocating them per product to get a
per-product break-even would require an arbitrary allocation key. The
standard CVP treatment works off the weighted-average contribution margin
ratio across the whole revenue base instead.

Only products with Product.unit_variable_cost set are included in the
revenue base this is computed against -- consistent with Profitability
Analysis, which never assumes a missing variable cost is zero. Their SKUs
are reported separately so it's visible when the numbers are incomplete.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import FixedCost, Product, SalesActual


@dataclass
class MarginalCostingSummary:
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


def summary(db: Session, company_id, fiscal_year: int) -> MarginalCostingSummary:
    products = {p.id: p for p in db.query(Product).filter(Product.company_id == company_id).all()}
    actuals = (
        db.query(SalesActual)
        .filter(
            SalesActual.company_id == company_id,
            SalesActual.period >= date(fiscal_year, 1, 1),
            SalesActual.period <= date(fiscal_year, 12, 31),
        )
        .all()
    )

    revenue = 0.0
    variable_cost = 0.0
    uncosted_skus: set = set()
    for a in actuals:
        product = products.get(a.product_id)
        if product is None or product.unit_variable_cost is None:
            if product is not None:
                uncosted_skus.add(product.sku)
            continue
        revenue += float(a.amount)
        variable_cost += float(product.unit_variable_cost) * float(a.quantity)

    revenue = round(revenue, 2)
    variable_cost = round(variable_cost, 2)
    contribution_margin = round(revenue - variable_cost, 2)
    cm_ratio = round((contribution_margin / revenue) * 100, 2) if revenue else None

    fixed_costs = round(
        sum(
            float(f.amount)
            for f in db.query(FixedCost).filter(FixedCost.company_id == company_id, FixedCost.fiscal_year == fiscal_year).all()
        ),
        2,
    )
    net_operating_income = round(contribution_margin - fixed_costs, 2)

    break_even_revenue = round(fixed_costs / (cm_ratio / 100), 2) if cm_ratio else None
    margin_of_safety = round(revenue - break_even_revenue, 2) if break_even_revenue is not None else None
    margin_of_safety_pct = round((margin_of_safety / revenue) * 100, 2) if margin_of_safety is not None and revenue else None
    degree_of_operating_leverage = (
        round(contribution_margin / net_operating_income, 2) if net_operating_income else None
    )

    return MarginalCostingSummary(
        fiscal_year=fiscal_year,
        revenue=revenue,
        variable_cost=variable_cost,
        contribution_margin=contribution_margin,
        contribution_margin_ratio=cm_ratio,
        fixed_costs=fixed_costs,
        net_operating_income=net_operating_income,
        break_even_revenue=break_even_revenue,
        margin_of_safety=margin_of_safety,
        margin_of_safety_pct=margin_of_safety_pct,
        degree_of_operating_leverage=degree_of_operating_leverage,
        uncosted_product_skus=sorted(uncosted_skus),
    )
