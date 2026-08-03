import sqlite3

from sqlalchemy import create_engine, inspect

from app.migrations import apply_additive_columns


def test_apply_additive_columns_adds_missing_columns(tmp_path):
    db_path = tmp_path / "old_schema.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE budgets (id TEXT PRIMARY KEY, name TEXT, type TEXT)")
    conn.execute("CREATE TABLE budget_lines (id TEXT PRIMARY KEY, budget_id TEXT, amount NUMERIC)")
    conn.execute("CREATE TABLE actual_lines (id TEXT PRIMARY KEY, amount NUMERIC)")
    conn.commit()
    conn.close()

    engine = create_engine(f"sqlite:///{db_path}")
    apply_additive_columns(engine)

    inspector = inspect(engine)
    assert "rolling_window_months" in {c["name"] for c in inspector.get_columns("budgets")}
    budget_line_cols = {c["name"] for c in inspector.get_columns("budget_lines")}
    assert {"justification", "variable_rate_per_unit", "useful_life_years", "annual_cash_flow"} <= budget_line_cols
    assert "actual_quantity" in {c["name"] for c in inspector.get_columns("actual_lines")}


def test_apply_additive_columns_is_idempotent(tmp_path):
    db_path = tmp_path / "already_current.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE budgets (id TEXT PRIMARY KEY, rolling_window_months INTEGER)")

    # running it twice on an already-current schema must not error
    apply_additive_columns(engine)
    apply_additive_columns(engine)

    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("budgets")]
    assert cols.count("rolling_window_months") == 1


def test_apply_additive_columns_skips_missing_tables(tmp_path):
    db_path = tmp_path / "no_tables.db"
    engine = create_engine(f"sqlite:///{db_path}")
    # no tables exist at all -- should be a no-op, not an error
    apply_additive_columns(engine)
