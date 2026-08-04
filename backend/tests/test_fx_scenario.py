def _upload_sales(client, company_id, sku, currency, rows):
    header = "sku,product_name,period,quantity,amount,currency\n"
    body = "".join(f"{sku},Widget,{period},{qty},{amount},{currency}\n" for period, qty, amount in rows)
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("s.csv", (header + body).encode(), "text/csv")})
    assert r.status_code == 200, r.text


def _set_rate(client, from_currency, to_currency, rate_date, rate):
    r = client.post("/exchange-rates", json={"from_currency": from_currency, "to_currency": to_currency, "rate_date": rate_date, "rate": rate})
    assert r.status_code == 200, r.text
    return r.json()


def test_exchange_rate_upsert_updates_in_place(client):
    r1 = _set_rate(client, "EUR", "USD", "2026-01-01", 1.10)
    r2 = _set_rate(client, "EUR", "USD", "2026-01-01", 1.12)
    assert r1["id"] == r2["id"]
    assert r2["rate"] == 1.12

    rates = client.get("/exchange-rates?from_currency=EUR&to_currency=USD").json()
    matches = [r for r in rates if r["rate_date"] == "2026-01-01"]
    assert len(matches) == 1
    assert matches[0]["rate"] == 1.12


def test_fx_exposure_converts_foreign_currency_sales(client, company):
    company_id = company["id"]  # base currency USD
    _set_rate(client, "EUR", "USD", "2026-01-01", 1.10)
    _upload_sales(client, company_id, "EU1", "EUR", [("2026-01", 10, 1000)])

    r = client.get(f"/fx/scenario?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-31&shock_pct=0")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["base_currency"] == "USD"
    assert len(body["lines"]) == 1
    line = body["lines"][0]
    assert line["currency"] == "EUR"
    assert line["native_amount"] == 1000
    assert line["rate_used"] == 1.10
    assert line["base_amount"] == 1100.0
    assert body["total_base_actual"] == 1100.0
    assert body["total_base_shocked"] == 1100.0
    assert body["impact"] == 0.0
    assert body["unrated_currencies"] == []


def test_fx_scenario_applies_shock(client, company):
    company_id = company["id"]
    _set_rate(client, "EUR", "USD", "2026-01-01", 1.00)
    _upload_sales(client, company_id, "EU2", "EUR", [("2026-01", 10, 1000)])

    r = client.get(f"/fx/scenario?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-31&shock_pct=10")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_base_actual"] == 1000.0
    assert body["total_base_shocked"] == 1100.0  # 10% appreciation
    assert body["impact"] == 100.0


def test_fx_scenario_flags_currencies_with_no_rate_on_file(client, company):
    company_id = company["id"]
    _upload_sales(client, company_id, "JP1", "JPY", [("2026-01", 10, 100000)])

    r = client.get(f"/fx/scenario?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-31&shock_pct=0")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lines"][0]["base_amount"] is None
    assert body["lines"][0]["rate_used"] is None
    assert body["unrated_currencies"] == ["JPY"]
    assert body["total_base_actual"] == 0.0  # nothing to sum -- no rate, no fabricated conversion


def test_fx_exposure_excludes_base_currency_sales(client, company):
    company_id = company["id"]
    _upload_sales(client, company_id, "US1", "USD", [("2026-01", 10, 1000)])

    r = client.get(f"/fx/scenario?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-31")
    assert r.status_code == 200, r.text
    assert r.json()["lines"] == []


def test_fx_uses_latest_rate_on_or_before_period(client, company):
    company_id = company["id"]
    _set_rate(client, "GBP", "USD", "2025-06-01", 1.20)
    _set_rate(client, "GBP", "USD", "2026-01-01", 1.30)
    _upload_sales(client, company_id, "GB1", "GBP", [("2026-06", 5, 500)])

    r = client.get(f"/fx/scenario?company_id={company_id}&start_period=2026-06-01&end_period=2026-06-30")
    body = r.json()
    assert body["lines"][0]["rate_used"] == 1.30  # most recent rate on/before June, not a future one
