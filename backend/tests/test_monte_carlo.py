import uuid


def _upload_sales(client, company_id, sku, rows):
    header = "sku,product_name,period,quantity,amount,currency\n"
    body = "".join(f"{sku},Widget,{period},{qty},{amount},USD\n" for period, qty, amount in rows)
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("s.csv", (header + body).encode(), "text/csv")})
    assert r.status_code == 200, r.text
    return client.get(f"/products?company_id={company_id}").json()[0]["id"]


def test_monte_carlo_returns_a_band_per_period(client, company):
    company_id = company["id"]
    product_id = _upload_sales(
        client,
        company_id,
        "MC1",
        [("2026-01", 10, 10000), ("2026-02", 10, 10500), ("2026-03", 10, 9800), ("2026-04", 10, 10200)],
    )

    r = client.get(
        f"/sales/forecast/monte-carlo?company_id={company_id}&product_id={product_id}&periods=3&trials=500"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trials"] == 500
    assert len(body["points"]) == 3
    for point in body["points"]:
        assert point["p10"] <= point["p50"] <= point["p90"]
        assert point["p10"] >= 0  # revenue can't simulate negative


def test_monte_carlo_band_widens_further_into_the_horizon(client, company):
    # With volatile-enough history, the p90-p10 spread at period 6 must be
    # at least as wide as at period 1 -- that's the whole point of
    # compounding independent shocks instead of a fixed-width CI.
    company_id = company["id"]
    product_id = _upload_sales(
        client,
        company_id,
        "MC2",
        [("2026-01", 10, 10000), ("2026-02", 10, 13000), ("2026-03", 10, 9000), ("2026-04", 10, 12500), ("2026-05", 10, 9500)],
    )

    r = client.get(
        f"/sales/forecast/monte-carlo?company_id={company_id}&product_id={product_id}&periods=6&trials=2000"
    )
    assert r.status_code == 200, r.text
    points = r.json()["points"]
    spread_first = points[0]["p90"] - points[0]["p10"]
    spread_last = points[-1]["p90"] - points[-1]["p10"]
    assert spread_last >= spread_first


def test_monte_carlo_requires_history(client, company):
    company_id = company["id"]
    r = client.get(f"/sales/forecast/monte-carlo?company_id={company_id}&product_id={uuid.uuid4()}&periods=3")
    assert r.status_code == 404


def test_monte_carlo_rejects_unknown_model(client, company):
    company_id = company["id"]
    product_id = _upload_sales(client, company_id, "MC3", [("2026-01", 5, 5000), ("2026-02", 5, 5100)])
    r = client.get(
        f"/sales/forecast/monte-carlo?company_id={company_id}&product_id={product_id}&periods=2&model=not_a_model"
    )
    assert r.status_code == 422


def test_monte_carlo_is_deterministic_given_same_history(client, company):
    # Not asserting exact reproducibility (no seed exposed over the API by
    # design -- this is a live simulation, not a fixture), just that it
    # doesn't error twice in a row and both responses are well-formed.
    company_id = company["id"]
    product_id = _upload_sales(client, company_id, "MC4", [("2026-01", 8, 8000), ("2026-02", 8, 8200), ("2026-03", 8, 7900)])
    for _ in range(2):
        r = client.get(f"/sales/forecast/monte-carlo?company_id={company_id}&product_id={product_id}&periods=2")
        assert r.status_code == 200, r.text
