import pytest


def _upload_sales(client, company_id, sku, amounts, start_month=1):
    lines = ["sku,product_name,period,quantity,amount,currency"]
    for i, amount in enumerate(amounts):
        lines.append(f"{sku},{sku},2026-{start_month + i:02d},10,{amount},USD")
    csv_content = ("\n".join(lines) + "\n").encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text


def _product_id(client, company_id, sku):
    r = client.get(f"/products?company_id={company_id}")
    return next(p["id"] for p in r.json() if p["sku"] == sku)


def _approved_expense_budget(client, company_id, period, amount, spent):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6000", "name": "Opex", "category": "expense"})
    gl_id = r.json()["id"]
    r = client.post(f"/budgets?company_id={company_id}", json={"name": "Opex Budget", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_id, "period": period, "amount": amount}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": period, "amount": spent})


def test_gross_margin_uses_only_priced_products(client, company):
    company_id = company["id"]
    _upload_sales(client, company_id, "PRICED", [12000])
    _upload_sales(client, company_id, "UNPRICED", [5000])
    priced_id = _product_id(client, company_id, "PRICED")
    client.patch(f"/products/{priced_id}", json={"unit_variable_cost": 700})  # unit price 1200, cost 700 -> 500 contribution/unit -> 41.7%

    r = client.get(f"/kpis?company_id={company_id}")
    assert r.status_code == 200, r.text
    assert r.json()["gross_margin_pct"] == pytest.approx(41.7, abs=0.1)


def test_gross_margin_none_without_any_pricing(client, company):
    company_id = company["id"]
    _upload_sales(client, company_id, "UNPRICED", [5000])
    r = client.get(f"/kpis?company_id={company_id}")
    assert r.json()["gross_margin_pct"] is None


def test_budget_utilization_pct(client, company):
    company_id = company["id"]
    _approved_expense_budget(client, company_id, "2026-08-01", 10000, 8700)
    r = client.get(f"/kpis?company_id={company_id}&fiscal_year=2026")
    assert r.json()["budget_utilization_pct"] == 87.0


def test_budget_utilization_none_without_approved_budgets(client, company):
    company_id = company["id"]
    r = client.get(f"/kpis?company_id={company_id}&fiscal_year=2026")
    assert r.json()["budget_utilization_pct"] is None


def test_forecast_accuracy_present_with_enough_history(client, company):
    company_id = company["id"]
    _upload_sales(client, company_id, "WIDGET", [100, 105, 98, 110, 102])  # 5 points, min backtest history is 3
    r = client.get(f"/kpis?company_id={company_id}")
    mape = r.json()["forecast_accuracy_mape"]
    assert mape is not None
    assert mape >= 0


def test_forecast_accuracy_none_with_insufficient_history(client, company):
    company_id = company["id"]
    _upload_sales(client, company_id, "WIDGET", [100, 105])  # only 2 points
    r = client.get(f"/kpis?company_id={company_id}")
    assert r.json()["forecast_accuracy_mape"] is None


def test_cash_runway_skipped_without_start_period(client, company):
    company_id = company["id"]
    r = client.get(f"/kpis?company_id={company_id}")
    assert r.json()["cash_runway_months"] is None


def test_cash_runway_detects_negative_balance(client, company):
    company_id = company["id"]
    client.post(f"/cashflow/items?company_id={company_id}", json={
        "category": "receivable_collection", "direction": "in", "period": "2026-07-01", "amount": 100,
    })
    client.post(f"/cashflow/items?company_id={company_id}", json={
        "category": "vendor_payment", "direction": "out", "period": "2026-08-01", "amount": 5000,
    })
    r = client.get(f"/kpis?company_id={company_id}&cash_start_period=2026-07-01&cash_opening_balance=0")
    assert r.json()["cash_runway_months"] == 1


def test_cash_runway_none_when_balance_stays_positive(client, company):
    company_id = company["id"]
    client.post(f"/cashflow/items?company_id={company_id}", json={
        "category": "receivable_collection", "direction": "in", "period": "2026-07-01", "amount": 100,
    })
    r = client.get(f"/kpis?company_id={company_id}&cash_start_period=2026-07-01&cash_opening_balance=1000")
    assert r.json()["cash_runway_months"] is None
