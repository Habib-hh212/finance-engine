def test_spend_anomaly_insight(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6500", "name": "Office Supplies", "category": "expense"})
    gl_id = r.json()["id"]

    # stable history (100 +/- 2) then a huge spike -- far outside its own norm
    amounts = [100, 102, 98, 100, 300]
    periods = ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"]
    for period, amount in zip(periods, amounts):
        r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": period, "amount": amount})
        assert r.status_code == 200, r.text

    rows = client.get(f"/ai/insights?company_id={company_id}").json()
    anomalies = [r for r in rows if r["type"] == "spend_anomaly"]
    assert len(anomalies) == 1
    assert anomalies[0]["severity"] == "red"
    assert "Office Supplies" in anomalies[0]["message"]
    assert "spiked" in anomalies[0]["message"]


def test_no_spend_anomaly_when_latest_is_within_normal_range(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6600", "name": "Steady Spend", "category": "expense"})
    gl_id = r.json()["id"]

    amounts = [100, 102, 98, 100, 101]  # last value is unremarkable
    periods = ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"]
    for period, amount in zip(periods, amounts):
        client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": period, "amount": amount})

    rows = client.get(f"/ai/insights?company_id={company_id}").json()
    assert [r for r in rows if r["type"] == "spend_anomaly"] == []


def test_sales_anomaly_insight(client, company):
    company_id = company["id"]
    csv_content = (
        b"sku,product_name,period,quantity,amount,currency\n"
        b"WIDGET-1,Widget,2026-01,10,1000,USD\n"
        b"WIDGET-1,Widget,2026-02,10,1010,USD\n"
        b"WIDGET-1,Widget,2026-03,10,990,USD\n"
        b"WIDGET-1,Widget,2026-04,10,1000,USD\n"
        b"WIDGET-1,Widget,2026-05,10,100,USD\n"  # sudden drop
    )
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text

    rows = client.get(f"/ai/insights?company_id={company_id}").json()
    anomalies = [r for r in rows if r["type"] == "sales_anomaly"]
    assert len(anomalies) == 1
    assert anomalies[0]["severity"] == "red"
    assert "dropped" in anomalies[0]["message"]


def test_anomaly_detection_needs_minimum_history(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6700", "name": "New Account", "category": "expense"})
    gl_id = r.json()["id"]
    # only 3 data points -- below MIN_ANOMALY_HISTORY(4)+1, so no anomaly check runs at all
    for i, period in enumerate(["2026-01-01", "2026-02-01", "2026-03-01"]):
        client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": period, "amount": 100 + i * 1000})

    rows = client.get(f"/ai/insights?company_id={company_id}").json()
    assert [r for r in rows if r["type"] == "spend_anomaly"] == []
