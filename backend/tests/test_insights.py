def _approved_expense_budget(client, company_id, code, name, period, amount, spent=None):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": name, "category": "expense"})
    gl_id = r.json()["id"]
    r = client.post(f"/budgets?company_id={company_id}", json={"name": name, "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_id, "period": period, "amount": amount}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    if spent is not None:
        client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": period, "amount": spent})
    return budget, gl_id


def test_budget_overrun_insight(client, company):
    company_id = company["id"]
    _approved_expense_budget(client, company_id, "6100", "Marketing", "2026-06-01", 10000, spent=11800)  # +18%

    rows = client.get(f"/ai/insights?company_id={company_id}&fiscal_year=2026").json()
    overrun = [r for r in rows if r["type"] == "budget_overrun"]
    assert len(overrun) == 1
    assert overrun[0]["severity"] == "red"
    assert "Marketing" in overrun[0]["message"]
    assert "18%" in overrun[0]["message"]


def test_revenue_shortfall_insight(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "4100", "name": "Product Sales", "category": "revenue"})
    gl_id = r.json()["id"]
    r = client.post(f"/budgets?company_id={company_id}", json={"name": "Rev Budget", "type": "revenue", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_id, "period": "2026-06-01", "amount": 10000}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": "2026-06-01", "amount": 8000})

    rows = client.get(f"/ai/insights?company_id={company_id}&fiscal_year=2026").json()
    shortfall = [r for r in rows if r["type"] == "revenue_shortfall"]
    assert len(shortfall) == 1
    assert shortfall[0]["severity"] == "red"
    assert "missed budget" in shortfall[0]["message"]


def test_unbudgeted_spend_insight(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6200", "name": "Rogue Spend", "category": "expense"})
    gl_id = r.json()["id"]
    client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": "2026-06-01", "amount": 3000})

    rows = client.get(f"/ai/insights?company_id={company_id}&fiscal_year=2026").json()
    unbudgeted = [r for r in rows if r["type"] == "unbudgeted_spend"]
    assert len(unbudgeted) == 1
    assert unbudgeted[0]["severity"] == "red"
    assert "Rogue Spend" in unbudgeted[0]["message"]


def test_budget_consumption_insight(client, company):
    company_id = company["id"]
    _approved_expense_budget(client, company_id, "6300", "Ops Budget", "2026-06-01", 10000, spent=8700)  # 87% consumed

    rows = client.get(f"/ai/insights?company_id={company_id}&fiscal_year=2026").json()
    consumption = [r for r in rows if r["type"] == "budget_consumption"]
    assert len(consumption) == 1
    assert consumption[0]["severity"] == "yellow"
    assert "87%" in consumption[0]["message"]


def test_no_insights_when_everything_is_on_track(client, company):
    company_id = company["id"]
    # 50% spent, -50% variance vs. budget: underspend is favorable (always green)
    # and 50% consumption is well under the 80% "watch" threshold.
    _approved_expense_budget(client, company_id, "6400", "Steady Budget", "2026-06-01", 10000, spent=5000)
    rows = client.get(f"/ai/insights?company_id={company_id}&fiscal_year=2026").json()
    assert rows == []


def test_forecast_decline_insight(client, company):
    company_id = company["id"]
    # flat baseline then a one-off spike: exponential smoothing lags, so its
    # level stays well below the spike -> forecast reads as a decline versus
    # the most recent actual.
    csv_content = (
        b"sku,product_name,period,quantity,amount,currency\n"
        b"SPIKY,Spiky,2026-01,1,100,USD\n"
        b"SPIKY,Spiky,2026-02,1,100,USD\n"
        b"SPIKY,Spiky,2026-03,1,100,USD\n"
        b"SPIKY,Spiky,2026-04,1,300,USD\n"
        b"STEADY,Steady,2026-01,1,100,USD\n"
        b"STEADY,Steady,2026-02,1,100,USD\n"
        b"STEADY,Steady,2026-03,1,100,USD\n"
        b"STEADY,Steady,2026-04,1,100,USD\n"
    )
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text

    rows = client.get(f"/ai/insights?company_id={company_id}").json()
    decline = [r for r in rows if r["type"] == "forecast_decline"]
    assert len(decline) == 1
    assert "Spiky" in decline[0]["message"]
    assert decline[0]["severity"] == "red"
