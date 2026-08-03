import pytest


def _upload_flat_sales(client, company_id, sku="WIDGET-1"):
    csv_content = (
        f"sku,product_name,period,quantity,amount,currency\n"
        f"{sku},Widget,2026-05,10,10000,USD\n"
        f"{sku},Widget,2026-06,10,10000,USD\n"
        f"{sku},Widget,2026-07,10,10000,USD\n"
    ).encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text


def _approved_budget_line(client, company_id, budget_type, gl_category, amount, period, code):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": "Test Account", "category": gl_category})
    gl_account_id = r.json()["id"]
    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": f"Budget {code}", "type": budget_type, "fiscal_year": 2026, "currency": "USD"},
    )
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_account_id, "period": period, "amount": amount}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    r = client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    assert r.json()["status"] == "approved"
    return gl_account_id, budget


def test_income_statement_forecast_revenue_and_expense(client, company):
    company_id = company["id"]
    _upload_flat_sales(client, company_id)
    _approved_budget_line(client, company_id, "expense", "expense", 4000, period="2026-08-01", code="6000")

    rows = client.get(f"/forecast/income-statement?company_id={company_id}&start_period=2026-08-01&periods=1").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["period"] == "2026-08-01"
    assert row["revenue_forecast"] == pytest.approx(10000, abs=0.5)
    assert row["expense_forecast"] == 4000
    assert row["net_profit_forecast"] == pytest.approx(6000, abs=0.5)


def test_income_statement_forecast_counts_expense_by_gl_category_not_budget_type(client, company):
    company_id = company["id"]
    _upload_flat_sales(client, company_id)
    # a "master" type budget with an expense-category GL account line must still count --
    # the income statement driver is the GL account's category, not the budget's own type.
    _approved_budget_line(client, company_id, "master", "expense", 1500, period="2026-08-01", code="6001")

    rows = client.get(f"/forecast/income-statement?company_id={company_id}&start_period=2026-08-01&periods=1").json()
    assert rows[0]["expense_forecast"] == 1500


def test_income_statement_forecast_covers_full_window_when_start_is_past_last_actual(client, company):
    # Sales history ends 2026-07. Forecasting from 2027-01 (six months past the
    # last actual) must still return revenue for every requested month, not
    # just however many months cashflow.forecast_sales_by_month happens to
    # generate counting from the last actual.
    company_id = company["id"]
    _upload_flat_sales(client, company_id)

    rows = client.get(f"/forecast/income-statement?company_id={company_id}&start_period=2027-01-01&periods=3").json()
    assert [r["period"] for r in rows] == ["2027-01-01", "2027-02-01", "2027-03-01"]
    for row in rows:
        assert row["revenue_forecast"] == pytest.approx(10000, abs=0.5)


def test_income_statement_forecast_excludes_draft_budgets(client, company):
    company_id = company["id"]
    _upload_flat_sales(client, company_id)
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6999", "name": "Draft Expense", "category": "expense"})
    gl_account_id = r.json()["id"]
    r = client.post(f"/budgets?company_id={company_id}", json={"name": "Draft Budget", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_account_id, "period": "2026-08-01", "amount": 9999}])
    # left in draft on purpose -- must not count

    rows = client.get(f"/forecast/income-statement?company_id={company_id}&start_period=2026-08-01&periods=1").json()
    assert rows[0]["expense_forecast"] == 0


def test_balance_sheet_forecast_drivers(client, company):
    company_id = company["id"]
    _upload_flat_sales(client, company_id)
    _approved_budget_line(client, company_id, "expense", "expense", 4000, period="2026-08-01", code="6100")

    accounts = {}
    for code, name, category, role in [
        ("1000", "Cash", "asset", "cash"),
        ("1100", "AR", "asset", "accounts_receivable"),
        ("1200", "Inventory", "asset", None),
        ("2000", "AP", "liability", "accounts_payable"),
        ("2100", "Accrued", "liability", None),
        ("3000", "Retained Earnings", "equity", None),
    ]:
        payload = {"code": code, "name": name, "category": category}
        if role:
            payload["forecast_role"] = role
        r = client.post(f"/gl-accounts?company_id={company_id}", json=payload)
        assert r.status_code == 200, r.text
        accounts[code] = r.json()["id"]

    opening_balances = {"1000": 2000, "1100": 3000, "1200": 1500, "2000": 800, "2100": 300, "3000": 5000}
    for code, amount in opening_balances.items():
        r = client.post(
            f"/actuals?company_id={company_id}",
            json={"gl_account_id": accounts[code], "period": "2026-01-01", "amount": amount},
        )
        assert r.status_code == 200, r.text

    r = client.get(
        f"/forecast/balance-sheet?company_id={company_id}&start_period=2026-08-01&periods=1"
        f"&dso_days=30&dpo_days=30&collection_lag_days=0"
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]

    assert row["accounts_receivable"] == pytest.approx(10000, abs=0.5)  # revenue * 30/30 dso
    assert row["accounts_payable"] == 4000  # expense * 30/30 dpo
    assert row["other_assets"] == 1500  # inventory carried flat; the AR-tagged account is excluded
    assert row["other_liabilities"] == 300  # accrued carried flat; the AP-tagged account is excluded
    assert row["cash"] == pytest.approx(8000, abs=0.5)  # 2000 opening + 10000 in - 4000 out, no collection lag
    assert row["total_assets"] == pytest.approx(19500, abs=1)
    assert row["total_liabilities"] == pytest.approx(4300, abs=1)
    assert row["equity"] == pytest.approx(11000, abs=1)  # 5000 base + 6000 net income
    assert row["difference"] == pytest.approx(row["total_assets"] - (row["total_liabilities"] + row["equity"]), abs=0.01)


def test_balance_sheet_forecast_with_no_data_balances_at_zero(client, company):
    company_id = company["id"]
    r = client.get(f"/forecast/balance-sheet?company_id={company_id}&start_period=2026-08-01&periods=1")
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row["total_assets"] == 0
    assert row["total_liabilities"] == 0
    assert row["equity"] == 0
    assert row["is_balanced"] is True
