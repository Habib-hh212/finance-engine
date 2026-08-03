import pytest


def _make_product(client, company_id, sku="WIDGET-1"):
    csv_content = (f"sku,product_name,period,quantity,amount,currency\n{sku},Widget,2026-01,10,1000,USD\n").encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text
    r = client.get(f"/products?company_id={company_id}")
    match = [p for p in r.json() if p["sku"] == sku]
    assert len(match) == 1
    return match[0]["id"]


def _set_standard_cost(client, company_id, product_id):
    r = client.post(
        f"/standard-costs?company_id={company_id}",
        json={
            "product_id": product_id,
            "material_std_price": 5,
            "material_std_qty": 2,
            "labor_std_rate": 20,
            "labor_std_hours": 1,
            "variable_overhead_std_rate": 3,
            "fixed_overhead_std_rate": 4,
            "fixed_overhead_budgeted": 1000,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_standard_cost_upsert_does_not_duplicate(client, company):
    company_id = company["id"]
    product_id = _make_product(client, company_id)
    _set_standard_cost(client, company_id, product_id)
    _set_standard_cost(client, company_id, product_id)  # second call updates in place

    rows = client.get(f"/standard-costs?company_id={company_id}").json()
    assert len([r for r in rows if r["product_id"] == product_id]) == 1


def test_eight_variance_method(client, company):
    company_id = company["id"]
    product_id = _make_product(client, company_id)
    _set_standard_cost(client, company_id, product_id)

    r = client.post(
        f"/production-actuals?company_id={company_id}",
        json={
            "product_id": product_id,
            "period": "2026-01-01",
            "units_produced": 100,
            "material_actual_price": 5.5,
            "material_actual_qty": 210,
            "labor_actual_rate": 21,
            "labor_actual_hours": 95,
            "actual_variable_overhead": 300,
            "actual_fixed_overhead": 1050,
        },
    )
    assert r.status_code == 200, r.text

    rows = client.get(f"/standard-costing/variance?company_id={company_id}&fiscal_year=2026").json()
    assert len(rows) == 1
    row = rows[0]

    # std_qty_allowed = 100*2=200; std_hours_allowed = 100*1=100
    assert row["material_price_variance"] == pytest.approx(-105)  # (5-5.5)*210
    assert row["material_quantity_variance"] == pytest.approx(-50)  # (200-210)*5
    assert row["material_total_variance"] == pytest.approx(-155)

    assert row["labor_rate_variance"] == pytest.approx(-95)  # (20-21)*95
    assert row["labor_efficiency_variance"] == pytest.approx(100)  # (100-95)*20
    assert row["labor_total_variance"] == pytest.approx(5)

    assert row["variable_overhead_spending_variance"] == pytest.approx(-15)  # 3*95 - 300
    assert row["variable_overhead_efficiency_variance"] == pytest.approx(15)  # (100-95)*3
    assert row["variable_overhead_total_variance"] == pytest.approx(0)

    assert row["fixed_overhead_budget_variance"] == pytest.approx(-50)  # 1000-1050
    assert row["fixed_overhead_volume_variance"] == pytest.approx(-600)  # 100*4 - 1000
    assert row["fixed_overhead_total_variance"] == pytest.approx(-650)

    assert row["total_cost_variance"] == pytest.approx(-800)


def test_variance_skips_products_without_a_standard(client, company):
    company_id = company["id"]
    product_id = _make_product(client, company_id, sku="NOSTD-1")
    # no standard cost set for this product
    client.post(
        f"/production-actuals?company_id={company_id}",
        json={
            "product_id": product_id,
            "period": "2026-01-01",
            "units_produced": 10,
            "material_actual_price": 1,
            "material_actual_qty": 1,
            "labor_actual_rate": 1,
            "labor_actual_hours": 1,
            "actual_variable_overhead": 1,
            "actual_fixed_overhead": 1,
        },
    )
    rows = client.get(f"/standard-costing/variance?company_id={company_id}&fiscal_year=2026").json()
    assert rows == []
