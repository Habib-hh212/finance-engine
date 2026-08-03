import pytest


def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _post_actual(client, company_id, gl_account_id, period, amount):
    r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_account_id, "period": period, "amount": amount})
    assert r.status_code == 200, r.text


def test_historical_trend_forecast_uses_full_actuals_history(client, company):
    company_id = company["id"]
    revenue_id = _gl_account(client, company_id, "4500", "revenue")
    expense_id = _gl_account(client, company_id, "6500", "expense")

    for month in ["2022-01", "2022-02", "2022-03", "2022-04"]:
        _post_actual(client, company_id, revenue_id, f"{month}-01", 10000)
        _post_actual(client, company_id, expense_id, f"{month}-01", 4000)

    r = client.get(
        f"/forecast/income-statement?company_id={company_id}&start_period=2022-05-01&periods=1"
        f"&forecast_method=historical_trend&trend_model=exponential_smoothing"
    )
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row["revenue_forecast"] == pytest.approx(10000, abs=0.5)
    assert row["expense_forecast"] == pytest.approx(4000, abs=0.5)
    assert row["net_profit_forecast"] == pytest.approx(6000, abs=0.5)


def test_historical_trend_forecast_requires_revenue_history(client, company):
    company_id = company["id"]
    expense_id = _gl_account(client, company_id, "6501", "expense")
    _post_actual(client, company_id, expense_id, "2022-01-01", 100)

    r = client.get(
        f"/forecast/income-statement?company_id={company_id}&start_period=2022-02-01&periods=1&forecast_method=historical_trend"
    )
    assert r.status_code == 422
    assert "revenue" in r.json()["detail"].lower()


def test_historical_trend_forecast_requires_expense_history(client, company):
    company_id = company["id"]
    revenue_id = _gl_account(client, company_id, "4501", "revenue")
    _post_actual(client, company_id, revenue_id, "2022-01-01", 100)

    r = client.get(
        f"/forecast/income-statement?company_id={company_id}&start_period=2022-02-01&periods=1&forecast_method=historical_trend"
    )
    assert r.status_code == 422
    assert "expense" in r.json()["detail"].lower()


def test_driver_based_remains_default_method(client, company):
    # forecast_method defaults to driver_based -- omitting it must behave
    # exactly as it always did, unaffected by the new historical_trend option.
    company_id = company["id"]
    r = client.get(f"/forecast/income-statement?company_id={company_id}&start_period=2022-02-01&periods=1")
    assert r.status_code == 200, r.text
    assert r.json()[0]["revenue_forecast"] == 0
