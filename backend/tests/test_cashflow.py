def _upload_sales_history(client, company_id):
    csv_content = (
        b"sku,product_name,period,quantity,amount,currency\n"
        b"WIDGET-1,Widget,2026-01,100,10000,USD\n"
        b"WIDGET-1,Widget,2026-02,110,11000,USD\n"
        b"WIDGET-1,Widget,2026-03,120,12500,USD\n"
        b"WIDGET-1,Widget,2026-04,115,11800,USD\n"
        b"WIDGET-1,Widget,2026-05,130,13200,USD\n"
        b"WIDGET-1,Widget,2026-06,140,14500,USD\n"
    )
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text


def _approved_expense_budget(client, company_id, period, amount):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6000", "name": "Payroll & Ops", "category": "expense"})
    gl_account_id = r.json()["id"]

    r = client.post(f"/budgets?company_id={company_id}", json={"name": "FY26 Opex", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()

    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_account_id, "period": period, "amount": amount}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    r = client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    assert r.json()["status"] == "approved"
    return budget


def _draft_expense_budget(client, company_id, period, amount):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6100", "name": "Unapproved Spend", "category": "expense"})
    gl_account_id = r.json()["id"]
    r = client.post(f"/budgets?company_id={company_id}", json={"name": "Pending Opex", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_account_id, "period": period, "amount": amount}])
    return budget  # left in 'draft' on purpose


def test_cash_flow_combines_sales_forecast_approved_budget_and_manual_items(client, company):
    company_id = company["id"]
    _upload_sales_history(client, company_id)

    # Approved budget line lands in 2026-08 and must count as cash out.
    _approved_expense_budget(client, company_id, "2026-08-01", 5000)
    # Draft budget line also in 2026-08, same month, must NOT count.
    _draft_expense_budget(client, company_id, "2026-08-01", 9999)

    # Manual items: payroll out in Aug, a receivable collection in in Sep.
    client.post(f"/cashflow/items?company_id={company_id}", json={
        "category": "payroll", "direction": "out", "period": "2026-08-01", "amount": 3000,
    })
    client.post(f"/cashflow/items?company_id={company_id}", json={
        "category": "receivable_collection", "direction": "in", "period": "2026-09-01", "amount": 2000,
    })

    # Sales history ends 2026-06; a 3-period forecast lands in Jul/Aug/Sep,
    # then a 30-day (~1 month) collection lag shifts those receipts to Aug/Sep/Oct.
    r = client.get(
        f"/cashflow/forecast?company_id={company_id}&start_period=2026-07-01&periods=4"
        f"&collection_lag_days=30&opening_balance=1000"
    )
    assert r.status_code == 200, r.text
    rows = {row["period"]: row for row in r.json()["rows"]}
    assert list(rows.keys()) == ["2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01"]

    jul, aug, sep, oct_ = rows["2026-07-01"], rows["2026-08-01"], rows["2026-09-01"], rows["2026-10-01"]

    # July: nothing has landed yet (lag pushes the first collection to August).
    assert jul["cash_in_forecast"] == 0
    assert jul["cash_out_budget"] == 0
    assert jul["opening_balance"] == 1000
    assert jul["closing_balance"] == 1000

    # August: sales-driven cash-in appears, approved budget counts, draft budget does not,
    # manual payroll outflow counts.
    assert aug["cash_in_forecast"] > 0
    assert aug["cash_out_budget"] == 5000
    assert aug["cash_out_manual"] == 3000
    forecast_level = aug["cash_in_forecast"]
    assert aug["opening_balance"] == jul["closing_balance"]
    assert aug["net_cash_flow"] == round(forecast_level - 5000 - 3000, 2)

    # September: same forecast level continues (exponential smoothing repeats its level),
    # plus the manual receivable collection, no budget outflow this month.
    assert sep["cash_in_forecast"] == forecast_level
    assert sep["cash_in_manual"] == 2000
    assert sep["cash_out_budget"] == 0
    assert sep["opening_balance"] == aug["closing_balance"]

    # October: forecast continues, nothing manual, running balance keeps compounding.
    assert oct_["cash_in_forecast"] == forecast_level
    assert oct_["cash_in_manual"] == 0
    assert oct_["opening_balance"] == sep["closing_balance"]
    assert oct_["closing_balance"] == round(
        1000 + (0) + (forecast_level - 5000 - 3000) + (forecast_level + 2000) + forecast_level, 2
    )


def test_cash_flow_with_no_data_is_all_zero_but_carries_opening_balance(client):
    r = client.post("/companies", json={"name": "Empty Co", "base_currency": "USD"})
    company_id = r.json()["id"]

    r = client.get(f"/cashflow/forecast?company_id={company_id}&start_period=2026-01-01&periods=2&opening_balance=500")
    rows = r.json()["rows"]
    assert len(rows) == 2
    for row in rows:
        assert row["cash_in_total"] == 0
        assert row["cash_out_total"] == 0
        assert row["net_cash_flow"] == 0
    assert rows[0]["opening_balance"] == 500
    assert rows[-1]["closing_balance"] == 500
