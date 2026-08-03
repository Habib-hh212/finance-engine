"""Bulk-imports historical financial statement actuals from an uploaded
Excel or CSV workbook into ActualLine, so a company's existing multi-year
financial history (three, four years, however much they have) can be loaded
in one shot instead of typed in month by month on the Controlling page.
This is what feeds the historical-trend forecast method in
statement_forecast.py, and there's no cap here on how many years a single
upload can cover.

Expected columns: gl_account_code, category (revenue/expense/asset/
liability/equity), period (YYYY-MM or YYYY-MM-DD), amount -- optional
gl_account_name (used only when the code doesn't already exist), currency
(defaults to the company's base currency), cost_center_code (optional,
tags the row for Cost Center Accounting reporting).
"""
import io
import uuid
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.models import ActualLine, Company, CostCenter, GLAccount

REQUIRED_COLUMNS = {"gl_account_code", "category", "period", "amount"}
VALID_CATEGORIES = {"revenue", "expense", "asset", "liability", "equity"}


def _parse_period(value) -> date:
    parsed = pd.to_datetime(value)
    return date(parsed.year, parsed.month, 1)


def _read_table(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    return pd.read_excel(io.BytesIO(file_bytes))


def import_statement_file(db: Session, company_id: uuid.UUID, file_bytes: bytes, filename: str) -> dict:
    df = _read_table(file_bytes, filename)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"File is missing required columns: {sorted(missing)}")

    company = db.get(Company, company_id)
    if company is None:
        raise ValueError("Company not found")

    accounts_by_code: dict[str, GLAccount] = {
        a.code: a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()
    }
    centers_by_code: dict[str, CostCenter] = {
        c.code: c for c in db.query(CostCenter).filter(CostCenter.company_id == company_id).all()
    }

    accounts_created = 0
    cost_centers_created = 0
    rows_imported = 0

    for row_num, row in df.iterrows():
        if pd.isna(row["gl_account_code"]) or pd.isna(row["category"]) or pd.isna(row["period"]) or pd.isna(row["amount"]):
            raise ValueError(f"Row {row_num + 2} is missing a required value (gl_account_code/category/period/amount)")

        code = str(row["gl_account_code"]).strip()
        category = str(row["category"]).strip().lower()
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}' for account {code}; must be one of {sorted(VALID_CATEGORIES)}"
            )

        account = accounts_by_code.get(code)
        if account is None:
            raw_name = row.get("gl_account_name")
            name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else code
            account = GLAccount(
                company_id=company_id,
                code=code,
                name=name,
                category=category,
            )
            db.add(account)
            db.flush()
            accounts_by_code[code] = account
            accounts_created += 1
        elif account.category != category:
            raise ValueError(
                f"Row category '{category}' for account {code} doesn't match its existing category '{account.category}'"
            )

        cost_center_id = None
        cost_center_code = row.get("cost_center_code")
        if isinstance(cost_center_code, str) and cost_center_code.strip():
            cost_center_code = cost_center_code.strip()
            center = centers_by_code.get(cost_center_code)
            if center is None:
                center = CostCenter(company_id=company_id, code=cost_center_code, name=cost_center_code)
                db.add(center)
                db.flush()
                centers_by_code[cost_center_code] = center
                cost_centers_created += 1
            cost_center_id = center.id

        raw_currency = row.get("currency")
        currency = raw_currency.strip().upper() if isinstance(raw_currency, str) and raw_currency.strip() else company.base_currency.upper()

        db.add(
            ActualLine(
                company_id=company_id,
                gl_account_id=account.id,
                period=_parse_period(row["period"]),
                amount=row["amount"],
                currency=currency,
                cost_center_id=cost_center_id,
            )
        )
        rows_imported += 1

    db.commit()
    return {
        "rows_imported": rows_imported,
        "accounts_created": accounts_created,
        "cost_centers_created": cost_centers_created,
    }
