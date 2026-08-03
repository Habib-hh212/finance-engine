"""Parses an uploaded sales CSV or Excel file and upserts
Product/Customer/SalesActual rows.

Expected columns: sku, product_name, period (YYYY-MM or YYYY-MM-DD),
quantity, amount, currency, customer_name (optional).
"""
import io
import uuid
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Customer, Product, SalesActual

REQUIRED_COLUMNS = {"sku", "period", "quantity", "amount", "currency"}


def _parse_period(value: str) -> date:
    parsed = pd.to_datetime(value)
    return date(parsed.year, parsed.month, 1)


def import_sales_file(db: Session, company_id: uuid.UUID, file_bytes: bytes, filename: str) -> dict:
    df = pd.read_csv(io.BytesIO(file_bytes)) if filename.lower().endswith(".csv") else pd.read_excel(io.BytesIO(file_bytes))
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    products_by_sku: dict[str, Product] = {
        p.sku: p for p in db.query(Product).filter(Product.company_id == company_id).all()
    }
    customers_by_name: dict[str, Customer] = {
        c.name: c for c in db.query(Customer).filter(Customer.company_id == company_id).all()
    }

    products_created = 0
    customers_created = 0
    rows_imported = 0

    for _, row in df.iterrows():
        sku = str(row["sku"])
        product = products_by_sku.get(sku)
        if product is None:
            product = Product(
                company_id=company_id,
                sku=sku,
                name=str(row.get("product_name", sku)),
            )
            db.add(product)
            db.flush()
            products_by_sku[sku] = product
            products_created += 1

        customer = None
        customer_name = row.get("customer_name")
        if isinstance(customer_name, str) and customer_name.strip():
            customer = customers_by_name.get(customer_name)
            if customer is None:
                customer = Customer(company_id=company_id, name=customer_name)
                db.add(customer)
                db.flush()
                customers_by_name[customer_name] = customer
                customers_created += 1

        db.add(
            SalesActual(
                company_id=company_id,
                product_id=product.id,
                customer_id=customer.id if customer else None,
                period=_parse_period(row["period"]),
                quantity=row["quantity"],
                amount=row["amount"],
                currency=str(row["currency"]).upper(),
            )
        )
        rows_imported += 1

    db.commit()
    return {
        "rows_imported": rows_imported,
        "products_created": products_created,
        "customers_created": customers_created,
    }
