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
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

# (table_name, column_name, DDL type string)
ADDITIVE_COLUMNS = [
    ("budgets", "rolling_window_months", "INTEGER"),
    ("budget_lines", "justification", "TEXT"),
    ("budget_lines", "variable_rate_per_unit", "NUMERIC(18,4)"),
    ("budget_lines", "useful_life_years", "INTEGER"),
    ("budget_lines", "annual_cash_flow", "NUMERIC(18,2)"),
    ("actual_lines", "actual_quantity", "NUMERIC(18,4)"),
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
