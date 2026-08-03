import pytest


def test_demand_forecast_uses_quantity_not_revenue(client, company):
    company_id = company["id"]
    # quantity is flat at 5 while amount (revenue) is 100 -- if the demand
    # endpoint accidentally forecasted revenue, forecast_units would come
    # back near 100, not 5.
    csv_content = (
        b"sku,product_name,period,quantity,amount,currency\n"
        b"WIDGET-1,Widget,2026-01,5,100,USD\n"
        b"WIDGET-1,Widget,2026-02,5,100,USD\n"
        b"WIDGET-1,Widget,2026-03,5,100,USD\n"
    )
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text
    product_id = client.get(f"/products?company_id={company_id}").json()[0]["id"]

    r = client.get(
        f"/sales/forecast/demand?company_id={company_id}&product_id={product_id}&model=moving_average&periods=1"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model"] == "moving_average"
    assert body["points"][0]["forecast_units"] == 5.0
    assert "currency" not in body["points"][0]


def test_demand_forecast_no_history_404s(client, company):
    company_id = company["id"]
    r = client.get(
        f"/sales/forecast/demand?company_id={company_id}&product_id=00000000-0000-0000-0000-000000000000"
    )
    assert r.status_code == 404


def _upload_customer_sales(client, company_id, customer_name, periods):
    rows = "\n".join(f"WIDGET-1,Widget,{period},1,100,USD,{customer_name}" for period in periods)
    csv_content = f"sku,product_name,period,quantity,amount,currency,customer_name\n{rows}\n".encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text


def test_churn_risk_flags_overdue_customer(client, company):
    company_id = company["id"]
    _upload_customer_sales(client, company_id, "Regular Co", ["2026-01", "2026-02", "2026-03"])

    r = client.get(f"/profitability/customer-churn-risk?company_id={company_id}&as_of=2026-08-01")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Regular Co"
    assert row["avg_order_interval_months"] == pytest.approx(1.0, abs=0.01)
    assert row["months_since_last_order"] == 5  # March -> August
    assert row["risk_level"] == "high"


def test_churn_risk_low_for_recently_active_customer(client, company):
    company_id = company["id"]
    _upload_customer_sales(client, company_id, "Loyal Co", ["2026-01", "2026-02", "2026-03"])

    r = client.get(f"/profitability/customer-churn-risk?company_id={company_id}&as_of=2026-04-01")
    rows = r.json()
    assert rows[0]["risk_level"] == "low"


def test_churn_risk_skips_single_order_customers(client, company):
    company_id = company["id"]
    _upload_customer_sales(client, company_id, "OneTime Co", ["2026-01"])

    r = client.get(f"/profitability/customer-churn-risk?company_id={company_id}")
    assert r.json() == []


def test_churn_risk_sorted_by_severity_then_ratio(client, company):
    company_id = company["id"]
    _upload_customer_sales(client, company_id, "Very Overdue", ["2026-01", "2026-02"])
    _upload_customer_sales(client, company_id, "Mildly Overdue", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])

    r = client.get(f"/profitability/customer-churn-risk?company_id={company_id}&as_of=2026-08-01")
    rows = r.json()
    names = [row["name"] for row in rows]
    assert names[0] == "Very Overdue"  # last order Feb, 1-month cadence -> ratio 6.0
