import pytest


def _upload_priced_sales(client, company_id, sku="WIDGET-1"):
    csv_content = (
        f"sku,product_name,period,quantity,amount,currency\n" f"{sku},Widget,2026-01,100,12000,USD\n" f"{sku},Widget,2026-02,100,12000,USD\n"
    ).encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text


def _get_product_id(client, company_id, sku="WIDGET-1"):
    r = client.get(f"/products?company_id={company_id}")
    match = [p for p in r.json() if p["sku"] == sku]
    assert len(match) == 1
    return match[0]["id"]


def test_fixed_cost_create_and_list(client, company):
    company_id = company["id"]
    r = client.post(f"/fixed-costs?company_id={company_id}", json={"fiscal_year": 2026, "name": "Rent", "amount": 2000})
    assert r.status_code == 200, r.text

    rows = client.get(f"/fixed-costs?company_id={company_id}&fiscal_year=2026").json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Rent"
    assert rows[0]["amount"] == 2000


def test_marginal_costing_summary(client, company):
    company_id = company["id"]
    _upload_priced_sales(client, company_id)
    product_id = _get_product_id(client, company_id)
    client.patch(f"/products/{product_id}", json={"unit_variable_cost": 70})
    client.post(f"/fixed-costs?company_id={company_id}", json={"fiscal_year": 2026, "name": "Rent", "amount": 3000})

    summary = client.get(f"/marginal-costing/summary?company_id={company_id}&fiscal_year=2026").json()

    # revenue 24000, variable cost 200*70=14000, contribution 10000, cm ratio ~41.67%
    assert summary["revenue"] == 24000
    assert summary["variable_cost"] == 14000
    assert summary["contribution_margin"] == 10000
    assert summary["contribution_margin_ratio"] == pytest.approx(41.67, abs=0.01)
    assert summary["fixed_costs"] == 3000
    assert summary["net_operating_income"] == 7000
    # break-even revenue = fixed costs / cm ratio ~= 3000 / 0.4167 ~= 7199.9
    assert summary["break_even_revenue"] == pytest.approx(7200, abs=5)
    assert summary["margin_of_safety"] == pytest.approx(24000 - summary["break_even_revenue"], abs=0.5)
    assert summary["margin_of_safety_pct"] == pytest.approx(70.0, abs=0.5)
    # DOL = contribution margin / net operating income = 10000/7000
    assert summary["degree_of_operating_leverage"] == pytest.approx(1.43, abs=0.01)
    assert summary["uncosted_product_skus"] == []


def test_marginal_costing_flags_uncosted_products(client, company):
    company_id = company["id"]
    _upload_priced_sales(client, company_id, sku="WIDGET-1")
    _upload_priced_sales(client, company_id, sku="UNCOSTED-1")
    product_id = _get_product_id(client, company_id, sku="WIDGET-1")
    client.patch(f"/products/{product_id}", json={"unit_variable_cost": 70})
    # UNCOSTED-1 is left with no unit_variable_cost set

    summary = client.get(f"/marginal-costing/summary?company_id={company_id}&fiscal_year=2026").json()

    assert "UNCOSTED-1" in summary["uncosted_product_skus"]
    # only WIDGET-1's revenue counts toward the totals
    assert summary["revenue"] == 24000


def test_marginal_costing_zero_revenue_returns_nulls_not_errors(client, company):
    company_id = company["id"]
    summary = client.get(f"/marginal-costing/summary?company_id={company_id}&fiscal_year=2026").json()
    assert summary["revenue"] == 0
    assert summary["contribution_margin_ratio"] is None
    assert summary["break_even_revenue"] is None
    assert summary["margin_of_safety"] is None
