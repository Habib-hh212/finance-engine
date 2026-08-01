def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": f"Account {code}", "category": category})
    assert r.status_code == 200, r.text
    return r.json()


def _approved_budget(client, company_id, budget_type, name, lines):
    """lines: list of (gl_account_id, period, amount)"""
    r = client.post(f"/budgets?company_id={company_id}", json={"name": name, "type": budget_type, "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_id, "period": period, "amount": amount} for gl_id, period, amount in lines],
    )
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    r = client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    assert r.json()["status"] == "approved"
    return budget


def _post_actual(client, company_id, gl_account_id, period, amount):
    r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_account_id, "period": period, "amount": amount})
    assert r.status_code == 200, r.text
    return r.json()


def _row_for(rows, gl_account_id, period):
    matches = [r for r in rows if r["gl_account_id"] == gl_account_id and r["period"] == period]
    assert len(matches) == 1, f"expected exactly one row for {gl_account_id}/{period}, got {matches}"
    return matches[0]


def test_expense_overrun_traffic_light_thresholds(client, company):
    company_id = company["id"]
    green_acc = _gl_account(client, company_id, "6001", "expense")
    yellow_acc = _gl_account(client, company_id, "6002", "expense")
    red_acc = _gl_account(client, company_id, "6003", "expense")

    _approved_budget(client, company_id, "expense", "Opex Green", [(green_acc["id"], "2026-08-01", 10000)])
    _approved_budget(client, company_id, "expense", "Opex Yellow", [(yellow_acc["id"], "2026-08-01", 10000)])
    _approved_budget(client, company_id, "expense", "Opex Red", [(red_acc["id"], "2026-08-01", 10000)])

    _post_actual(client, company_id, green_acc["id"], "2026-08-01", 10200)   # +2%  -> green
    _post_actual(client, company_id, yellow_acc["id"], "2026-08-01", 10600)  # +6%  -> yellow
    _post_actual(client, company_id, red_acc["id"], "2026-08-01", 12000)     # +20% -> red

    r = client.get(f"/variance/budget-vs-actual?company_id={company_id}&fiscal_year=2026")
    assert r.status_code == 200, r.text
    rows = r.json()

    assert _row_for(rows, green_acc["id"], "2026-08-01")["status"] == "green"
    assert _row_for(rows, yellow_acc["id"], "2026-08-01")["status"] == "yellow"
    row_red = _row_for(rows, red_acc["id"], "2026-08-01")
    assert row_red["status"] == "red"
    assert row_red["variance_amount"] == 2000
    assert row_red["variance_pct"] == 20.0


def test_expense_underspend_is_always_green(client, company):
    company_id = company["id"]
    acc = _gl_account(client, company["id"], "6004", "expense")
    _approved_budget(client, company_id, "expense", "Opex Underspend", [(acc["id"], "2026-08-01", 10000)])
    _post_actual(client, company_id, acc["id"], "2026-08-01", 4000)  # 60% underspend

    rows = client.get(f"/variance/budget-vs-actual?company_id={company_id}&fiscal_year=2026").json()
    assert _row_for(rows, acc["id"], "2026-08-01")["status"] == "green"


def test_revenue_shortfall_and_overachievement_directions(client, company):
    company_id = company["id"]
    shortfall_acc = _gl_account(client, company_id, "4001", "revenue")
    beat_acc = _gl_account(client, company_id, "4002", "revenue")

    _approved_budget(client, company_id, "revenue", "Rev Shortfall", [(shortfall_acc["id"], "2026-09-01", 10000)])
    _approved_budget(client, company_id, "revenue", "Rev Beat", [(beat_acc["id"], "2026-09-01", 10000)])

    _post_actual(client, company_id, shortfall_acc["id"], "2026-09-01", 8000)  # -20% -> unfavorable -> red
    _post_actual(client, company_id, beat_acc["id"], "2026-09-01", 12000)      # +20% -> favorable -> green

    rows = client.get(f"/variance/budget-vs-actual?company_id={company_id}&fiscal_year=2026").json()
    assert _row_for(rows, shortfall_acc["id"], "2026-09-01")["status"] == "red"
    assert _row_for(rows, beat_acc["id"], "2026-09-01")["status"] == "green"


def test_unapproved_budget_excluded_from_variance(client, company):
    company_id = company["id"]
    acc = _gl_account(client, company_id, "6005", "expense")

    r = client.post(f"/budgets?company_id={company_id}", json={"name": "Draft Opex", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": acc["id"], "period": "2026-08-01", "amount": 5000}])
    # left in 'draft' — never submitted/approved

    _post_actual(client, company_id, acc["id"], "2026-08-01", 3000)

    rows = client.get(f"/variance/budget-vs-actual?company_id={company_id}&fiscal_year=2026").json()
    row = _row_for(rows, acc["id"], "2026-08-01")
    # unapproved budget doesn't count, so this reads as unbudgeted spend
    assert row["budget_amount"] == 0
    assert row["actual_amount"] == 3000
    assert row["status"] == "red"


def test_budget_consumption_traffic_light(client, company):
    company_id = company["id"]

    green_acc = _gl_account(client, company_id, "6006", "expense")
    green_budget = _approved_budget(client, company_id, "expense", "Consumption Green", [(green_acc["id"], "2026-10-01", 10000)])
    _post_actual(client, company_id, green_acc["id"], "2026-10-01", 5000)  # 50%

    yellow_acc = _gl_account(client, company_id, "6007", "expense")
    yellow_budget = _approved_budget(client, company_id, "expense", "Consumption Yellow", [(yellow_acc["id"], "2026-10-01", 10000)])
    _post_actual(client, company_id, yellow_acc["id"], "2026-10-01", 8700)  # 87%, matches the roadmap example

    red_acc = _gl_account(client, company_id, "6008", "expense")
    red_budget = _approved_budget(client, company_id, "expense", "Consumption Red", [(red_acc["id"], "2026-10-01", 10000)])
    _post_actual(client, company_id, red_acc["id"], "2026-10-01", 11000)  # 110%, overrun

    g = client.get(f"/variance/budget-consumption/{green_budget['id']}").json()
    assert g["status"] == "green"
    assert g["remaining"] == 5000

    y = client.get(f"/variance/budget-consumption/{yellow_budget['id']}").json()
    assert y["status"] == "yellow"
    assert y["spent"] == 8700
    assert y["remaining"] == 1300
    assert y["consumption_pct"] == 87.0

    red = client.get(f"/variance/budget-consumption/{red_budget['id']}").json()
    assert red["status"] == "red"
    assert red["remaining"] == -1000
