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


def _approved_expense_budget(client, company_id, amount, period="2026-08-01", code="6100"):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": "Ops Expense", "category": "expense"})
    gl_account_id = r.json()["id"]
    r = client.post(f"/budgets?company_id={company_id}", json={"name": "FY26 Opex", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl_account_id, "period": period, "amount": amount}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    r = client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})
    assert r.json()["status"] == "approved"


def test_scenario_crud(client, company):
    company_id = company["id"]
    r = client.post(
        f"/scenarios?company_id={company_id}",
        json={"name": "Optimistic", "description": "Sales up, costs down", "sales_growth_pct": 10, "expense_growth_pct": -20},
    )
    assert r.status_code == 200, r.text
    scenario = r.json()
    assert scenario["sales_growth_pct"] == 10
    assert scenario["expense_growth_pct"] == -20

    r = client.get(f"/scenarios?company_id={company_id}")
    assert len(r.json()) == 1

    r = client.delete(f"/scenarios/{scenario['id']}")
    assert r.status_code == 204
    assert client.get(f"/scenarios?company_id={company_id}").json() == []


def test_scenario_forecast_applies_growth_to_income_statement(client, company):
    company_id = company["id"]
    _upload_flat_sales(client, company_id)
    _approved_expense_budget(client, company_id, 4000, period="2026-08-01")

    r = client.post(
        f"/scenarios?company_id={company_id}",
        json={"name": "Optimistic", "sales_growth_pct": 10, "expense_growth_pct": -20},
    )
    scenario_id = r.json()["id"]

    r = client.get(f"/scenarios/{scenario_id}/forecast?start_period=2026-08-01&periods=1")
    assert r.status_code == 200, r.text
    body = r.json()

    base = body["base_income_statement"][0]
    scenario = body["scenario_income_statement"][0]

    assert base["revenue_forecast"] == pytest.approx(10000, abs=0.5)
    assert base["expense_forecast"] == 4000
    assert base["net_profit_forecast"] == pytest.approx(6000, abs=0.5)

    assert scenario["revenue_forecast"] == pytest.approx(11000, abs=0.5)  # +10%
    assert scenario["expense_forecast"] == pytest.approx(3200, abs=0.5)  # -20%
    assert scenario["net_profit_forecast"] == pytest.approx(7800, abs=1)


def test_scenario_forecast_applies_growth_to_balance_sheet(client, company):
    company_id = company["id"]
    _upload_flat_sales(client, company_id)
    _approved_expense_budget(client, company_id, 4000, period="2026-08-01")

    r = client.post(
        f"/scenarios?company_id={company_id}",
        json={"name": "Optimistic", "sales_growth_pct": 10, "expense_growth_pct": -20},
    )
    scenario_id = r.json()["id"]

    r = client.get(
        f"/scenarios/{scenario_id}/forecast?start_period=2026-08-01&periods=1"
        f"&dso_days=30&dpo_days=30&collection_lag_days=0"
    )
    assert r.status_code == 200, r.text
    body = r.json()

    base = body["base_balance_sheet"][0]
    scenario = body["scenario_balance_sheet"][0]

    assert base["accounts_receivable"] == pytest.approx(10000, abs=0.5)
    assert base["accounts_payable"] == 4000
    assert base["cash"] == pytest.approx(6000, abs=0.5)  # 0 opening + 10000 in - 4000 out, no lag

    assert scenario["accounts_receivable"] == pytest.approx(11000, abs=0.5)
    assert scenario["accounts_payable"] == pytest.approx(3200, abs=0.5)
    assert scenario["cash"] == pytest.approx(7800, abs=1)  # 0 opening + 11000 in - 3200 out


def test_scenario_forecast_missing_scenario_404s(client, company):
    r = client.get("/scenarios/00000000-0000-0000-0000-000000000000/forecast?start_period=2026-08-01")
    assert r.status_code == 404
