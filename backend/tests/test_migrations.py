import sqlite3
import uuid

from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401 - registers all tables on Base.metadata
from app.database import Base
from app.migrations import apply_additive_columns, backfill_company_memberships


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


def test_backfill_company_memberships_grants_existing_users_on_orphaned_companies(tmp_path):
    # Regression test: this crashed on sqlite (though not on production's
    # Postgres) because uuid.uuid4() was bound as a raw uuid.UUID object,
    # which sqlite3's driver can't adapt -- only reproduces with real,
    # pre-existing rows that predate the CompanyMembership table, which no
    # other test happens to set up.
    db_path = tmp_path / "pre_existing_data.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    user_id, company_id = str(uuid.uuid4()), str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, name, created_at) "
                "VALUES (:id, :email, 'x', 'Old User', '2025-01-01 00:00:00')"
            ),
            {"id": user_id, "email": "old-user@example.com"},
        )
        conn.execute(
            text("INSERT INTO companies (id, name, base_currency) VALUES (:id, 'Old Co', 'USD')"),
            {"id": company_id},
        )

    backfill_company_memberships(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT user_id, company_id FROM company_memberships")).all()
    assert [(str(r.user_id), str(r.company_id)) for r in rows] == [(user_id, company_id)]


def test_backfill_company_memberships_is_idempotent(tmp_path):
    # Running it twice back-to-back (e.g. two app instances starting up at
    # once) must not grant duplicate membership rows for the same company
    # once it's no longer orphaned.
    db_path = tmp_path / "idempotent.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    user_id, company_id = str(uuid.uuid4()), str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, name, created_at) "
                "VALUES (:id, :email, 'x', 'Old User', '2025-01-01 00:00:00')"
            ),
            {"id": user_id, "email": "old-user-2@example.com"},
        )
        conn.execute(
            text("INSERT INTO companies (id, name, base_currency) VALUES (:id, 'Old Co', 'USD')"),
            {"id": company_id},
        )

    backfill_company_memberships(engine)
    backfill_company_memberships(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM company_memberships")).all()
    assert len(rows) == 1


def test_backfill_company_memberships_does_not_touch_companies_that_already_have_a_membership(tmp_path):
    # A company created after this migration shipped (via api/companies.py,
    # which grants membership to its creator at creation time) must not
    # additionally get every other user backfilled onto it.
    db_path = tmp_path / "not_orphaned.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    owner_id, other_user_id, company_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    with engine.begin() as conn:
        for uid, email in [(owner_id, "owner@example.com"), (other_user_id, "other@example.com")]:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, hashed_password, name, created_at) "
                    "VALUES (:id, :email, 'x', 'User', '2025-01-01 00:00:00')"
                ),
                {"id": uid, "email": email},
            )
        conn.execute(
            text("INSERT INTO companies (id, name, base_currency) VALUES (:id, 'New Co', 'USD')"),
            {"id": company_id},
        )
        conn.execute(
            text("INSERT INTO company_memberships (id, company_id, user_id) VALUES (:id, :company_id, :user_id)"),
            {"id": str(uuid.uuid4()), "company_id": company_id, "user_id": owner_id},
        )

    backfill_company_memberships(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT user_id FROM company_memberships")).all()
    assert [str(r.user_id) for r in rows] == [owner_id]
