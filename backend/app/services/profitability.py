"""Contribution margin (price - variable cost), per product and per customer.

Phase 1 keeps this light: it's derived entirely from SalesActual and
Product.unit_variable_cost, which the Sales Forecasting module already
captures — no separate costing module needed yet. Products without a
unit_variable_cost set are included with a null contribution rather than
silently assumed to have zero variable cost.
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Customer, Product, SalesActual


@dataclass
class ProductProfitability:
    product_id: object
    sku: str
    name: str
    quantity: float
    revenue: float
    unit_price: Optional[float]
    unit_variable_cost: Optional[float]
    contribution_per_unit: Optional[float]
    contribution_margin_total: Optional[float]
    contribution_margin_pct: Optional[float]


@dataclass
class CustomerProfitability:
    customer_id: object
    name: str
    revenue: float
    contribution_margin_total: Optional[float]
    contribution_margin_pct: Optional[float]


def by_product(db: Session, company_id) -> list:
    products = db.query(Product).filter(Product.company_id == company_id).all()
    actuals = db.query(SalesActual).filter(SalesActual.company_id == company_id).all()

    qty_by_product: dict = defaultdict(float)
    revenue_by_product: dict = defaultdict(float)
    for a in actuals:
        qty_by_product[a.product_id] += float(a.quantity)
        revenue_by_product[a.product_id] += float(a.amount)

    rows = []
    for product in products:
        quantity = round(qty_by_product.get(product.id, 0.0), 4)
        revenue = round(revenue_by_product.get(product.id, 0.0), 2)
        unit_price = round(revenue / quantity, 4) if quantity else None
        unit_variable_cost = float(product.unit_variable_cost) if product.unit_variable_cost is not None else None

        contribution_per_unit = None
        contribution_margin_total = None
        contribution_margin_pct = None
        if unit_price is not None and unit_variable_cost is not None:
            contribution_per_unit = round(unit_price - unit_variable_cost, 4)
            contribution_margin_total = round(contribution_per_unit * quantity, 2)
            contribution_margin_pct = round((contribution_per_unit / unit_price) * 100, 1) if unit_price else None

        rows.append(
            ProductProfitability(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                quantity=quantity,
                revenue=revenue,
                unit_price=unit_price,
                unit_variable_cost=unit_variable_cost,
                contribution_per_unit=contribution_per_unit,
                contribution_margin_total=contribution_margin_total,
                contribution_margin_pct=contribution_margin_pct,
            )
        )
    return rows


def by_customer(db: Session, company_id) -> list:
    customers = {c.id: c for c in db.query(Customer).filter(Customer.company_id == company_id).all()}
    products = {p.id: p for p in db.query(Product).filter(Product.company_id == company_id).all()}
    actuals = (
        db.query(SalesActual)
        .filter(SalesActual.company_id == company_id, SalesActual.customer_id.isnot(None))
        .all()
    )

    revenue_by_customer: dict = defaultdict(float)
    contribution_by_customer: dict = defaultdict(float)
    has_full_cost_data: dict = defaultdict(lambda: True)

    for a in actuals:
        revenue_by_customer[a.customer_id] += float(a.amount)
        product = products.get(a.product_id)
        if product is not None and product.unit_variable_cost is not None:
            contribution_by_customer[a.customer_id] += float(a.amount) - float(product.unit_variable_cost) * float(a.quantity)
        else:
            has_full_cost_data[a.customer_id] = False

    rows = []
    for customer_id, revenue in revenue_by_customer.items():
        customer = customers.get(customer_id)
        if customer is None:
            continue
        complete = has_full_cost_data[customer_id]
        contribution_margin_total = round(contribution_by_customer[customer_id], 2) if complete else None
        contribution_margin_pct = round((contribution_margin_total / revenue) * 100, 1) if complete and revenue else None
        rows.append(
            CustomerProfitability(
                customer_id=customer_id,
                name=customer.name,
                revenue=round(revenue, 2),
                contribution_margin_total=contribution_margin_total,
                contribution_margin_pct=contribution_margin_pct,
            )
        )
    return rows
