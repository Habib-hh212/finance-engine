"""Self-healing schema patch for additive column changes.

There's no Alembic (or any migration framework) in this project --
`Base.metadata.create_all()` in the app lifespan creates missing *tables*
just fine, but it silently does nothing for a column added to a table that
already exists. That gap was real: `budgets.rolling_window_months` and
`actual_lines.actual_quantity` shipped to production without ever reaching
the live Postgres database, and every budget creation and actuals post
failed with a 500 until this was caught.

This module inspects the live schema on startup and adds any column listed
below that's missing, using each column's declared SQLAlchemy type so the
DDL is correct on both SQLite (dev/tests) and Postgres (production). It
only ever adds nullable columns -- it does not rename, drop, or alter
existing columns, and it is not a substitute for real migration tooling if
this project ever needs anything less trivial than "new nullable column."

Whenever a new column is added to an *already-existing* table, add an
entry here in the same change -- this is the only thing standing between
"model changed" and "production silently broken."
"""
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# (table_name, column_name, DDL type string)
ADDITIVE_COLUMNS = [
    ("budgets", "rolling_window_months", "INTEGER"),
    ("budget_lines", "justification", "TEXT"),
    ("budget_lines", "variable_rate_per_unit", "NUMERIC(18,4)"),
    ("budget_lines", "useful_life_years", "INTEGER"),
    ("budget_lines", "annual_cash_flow", "NUMERIC(18,2)"),
    ("actual_lines", "actual_quantity", "NUMERIC(18,4)"),
    ("gl_accounts", "forecast_role", "VARCHAR(30)"),
    ("actual_lines", "cost_center_id", "UUID"),
    ("budget_lines", "cost_center_id", "UUID"),
    ("actual_lines", "journal_entry_line_id", "UUID"),
    ("journal_entry_lines", "tax_code_id", "UUID"),
    ("journal_entry_lines", "tax_amount", "NUMERIC(18,2)"),
]


def apply_additive_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, column, ddl_type in ADDITIVE_COLUMNS:
            if table not in existing_tables:
                continue  # create_all will make the table with this column already on it
            existing_columns = {c["name"] for c in inspector.get_columns(table)}
            if column in existing_columns:
                continue
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def backfill_company_memberships(engine: Engine) -> None:
    """One-time transition for per-company access control: every company
    that predates the CompanyMembership table has no membership rows at
    all, which would lock every existing user out of their own data the
    moment access checks go live. Rather than guess who "owns" a
    pre-existing company, this grants every existing user access to every
    company that currently has zero memberships -- exactly preserving the
    "any logged-in user can see any company" behavior that was already
    true for that data, while every *new* company created from here on
    only grants membership to its actual creator (see api/companies.py).
    Safe to run on every startup: a company only qualifies while it still
    has zero memberships, so this never re-grants access someone removed.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if "company_memberships" not in existing_tables or "companies" not in existing_tables or "users" not in existing_tables:
        return

    with engine.begin() as conn:
        orphan_companies = [
            row[0]
            for row in conn.execute(
                text("SELECT c.id FROM companies c LEFT JOIN company_memberships m ON m.company_id = c.id WHERE m.id IS NULL")
            )
        ]
        if not orphan_companies:
            return
        user_ids = [row[0] for row in conn.execute(text("SELECT id FROM users"))]
        for company_id in orphan_companies:
            for user_id in user_ids:
                conn.execute(
                    text("INSERT INTO company_memberships (id, company_id, user_id) VALUES (:id, :company_id, :user_id)"),
                    # Stringify every UUID: psycopg2 (prod) adapts raw uuid.UUID
                    # objects automatically, but sqlite3's driver (dev/test)
                    # doesn't and raises a binding error -- strings work on both.
                    {"id": str(uuid.uuid4()), "company_id": str(company_id), "user_id": str(user_id)},
                )
