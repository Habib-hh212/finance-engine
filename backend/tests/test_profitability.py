import pytest


def _upload_priced_sales(client, company_id, customer_name="Acme Buyer"):
    csv_content = (
        f"sku,product_name,period,quantity,amount,currency,customer_name\n"
        f"WIDGET-1,Widget,2026-01,100,12000,USD,{customer_name}\n"
        f"WIDGET-1,Widget,2026-02,100,12000,USD,{customer_name}\n"
    ).encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text


def _get_product_id(client, company_id, sku="WIDGET-1"):
    r = client.get(f"/products?company_id={company_id}")
    match = [p for p in r.json() if p["sku"] == sku]
    assert len(match) == 1
    return match[0]["id"]


def test_contribution_margin_by_product(client, company):
    company_id = company["id"]
    _upload_priced_sales(client, company_id)
    product_id = _get_product_id(client, company_id)

    # revenue 24000 over 200 units -> unit_price 120; set variable cost 70 -> contribution 50/unit
    r = client.patch(f"/products/{product_id}", json={"unit_variable_cost": 70})
    assert r.status_code == 200, r.text

    rows = client.get(f"/profitability/by-product?company_id={company_id}").json()
    row = next(r for r in rows if r["product_id"] == product_id)
    assert row["quantity"] == 200
    assert row["revenue"] == 24000
    assert row["unit_price"] == 120
    assert row["contribution_per_unit"] == 50
    assert row["contribution_margin_total"] == 10000
    assert row["contribution_margin_pct"] == pytest.approx(41.7, abs=0.1)


def test_product_without_cost_has_null_contribution(client, company):
    company_id = company["id"]
    _upload_priced_sales(client, company_id)
    product_id = _get_product_id(client, company_id)

    rows = client.get(f"/profitability/by-product?company_id={company_id}").json()
    row = next(r for r in rows if r["product_id"] == product_id)
    assert row["unit_price"] == 120
    assert row["unit_variable_cost"] is None
    assert row["contribution_per_unit"] is None
    assert row["contribution_margin_total"] is None


def test_contribution_margin_by_customer(client, company):
    company_id = company["id"]
    _upload_priced_sales(client, company_id, customer_name="Big Buyer Inc")
    product_id = _get_product_id(client, company_id)
    client.patch(f"/products/{product_id}", json={"unit_variable_cost": 70})

    rows = client.get(f"/profitability/by-customer?company_id={company_id}").json()
    row = next(r for r in rows if r["name"] == "Big Buyer Inc")
    assert row["revenue"] == 24000
    assert row["contribution_margin_total"] == 10000
    assert row["contribution_margin_pct"] == pytest.approx(41.7, abs=0.1)
