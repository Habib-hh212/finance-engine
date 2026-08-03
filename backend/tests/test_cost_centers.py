def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _cost_center(client, company_id, code, name="Marketing"):
    r = client.post(f"/cost-centers?company_id={company_id}", json={"code": code, "name": name})
    assert r.status_code == 200, r.text
    return r.json()


def test_create_and_list_cost_centers(client, company):
    company_id = company["id"]
    _cost_center(client, company_id, "CC-100", "Marketing")
    _cost_center(client, company_id, "CC-200", "Engineering")

    r = client.get(f"/cost-centers?company_id={company_id}")
    assert r.status_code == 200, r.text
    codes = {c["code"] for c in r.json()}
    assert {"CC-100", "CC-200"} <= codes


def test_actual_line_can_be_tagged_with_cost_center(client, company):
    company_id = company["id"]
    gl_id = _gl_account(client, company_id, "6500", "expense")
    center = _cost_center(client, company_id, "CC-300")

    r = client.post(
        f"/actuals?company_id={company_id}",
        json={"gl_account_id": gl_id, "period": "2026-01-01", "amount": 1000, "cost_center_id": center["id"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["cost_center_id"] == center["id"]


def test_cost_center_variance_compares_budget_and_actual(client, company):
    company_id = company["id"]
    gl_id = _gl_account(client, company_id, "6501", "expense")
    center = _cost_center(client, company_id, "CC-400", "Sales")

    r = client.post(f"/budgets?company_id={company_id}", json={"name": "Sales Budget", "type": "expense", "fiscal_year": 2026, "currency": "USD"})
    budget = r.json()
    client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_id, "period": "2026-03-01", "amount": 5000, "cost_center_id": center["id"]}],
    )
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Finance Fay"})
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "CFO Cara"})

    client.post(
        f"/actuals?company_id={company_id}",
        json={"gl_account_id": gl_id, "period": "2026-03-01", "amount": 6000, "cost_center_id": center["id"]},
    )

    r = client.get(f"/variance/cost-center?company_id={company_id}&fiscal_year=2026")
    assert r.status_code == 200, r.text
    rows = [row for row in r.json() if row["cost_center_id"] == center["id"]]
    assert len(rows) == 1
    row = rows[0]
    assert row["budget_amount"] == 5000
    assert row["actual_amount"] == 6000
    assert row["variance_amount"] == 1000
    assert row["status"] == "red"  # 20% over budget, spending more than budgeted is unfavorable


def test_cost_center_variance_excludes_untagged_lines(client, company):
    company_id = company["id"]
    gl_id = _gl_account(client, company_id, "6502", "expense")

    client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_id, "period": "2026-04-01", "amount": 500})

    r = client.get(f"/variance/cost-center?company_id={company_id}")
    assert r.status_code == 200, r.text
    assert r.json() == []
