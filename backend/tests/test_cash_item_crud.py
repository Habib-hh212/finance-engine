import uuid


def _create_item(client, company_id, amount=500, category="payroll", direction="out", period="2026-03-01"):
    r = client.post(
        f"/cashflow/items?company_id={company_id}",
        json={"category": category, "direction": direction, "period": period, "amount": amount},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_cash_item_can_be_updated(client, company):
    company_id = company["id"]
    item = _create_item(client, company_id, amount=500)

    r = client.patch(f"/cashflow/items/{item['id']}?company_id={company_id}", json={"amount": 750})
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 750

    items = client.get(f"/cashflow/items?company_id={company_id}").json()
    matches = [i for i in items if i["id"] == item["id"]]
    assert len(matches) == 1
    assert matches[0]["amount"] == 750


def test_cash_item_update_can_change_multiple_fields(client, company):
    company_id = company["id"]
    item = _create_item(client, company_id, category="payroll", direction="out")

    r = client.patch(
        f"/cashflow/items/{item['id']}?company_id={company_id}",
        json={"category": "tax", "direction": "in", "description": "Corrected entry"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"] == "tax"
    assert body["direction"] == "in"
    assert body["description"] == "Corrected entry"
    assert body["amount"] == 500  # untouched fields stay as-is


def test_cash_item_can_be_deleted(client, company):
    company_id = company["id"]
    item = _create_item(client, company_id)

    r = client.delete(f"/cashflow/items/{item['id']}?company_id={company_id}")
    assert r.status_code == 204

    items = client.get(f"/cashflow/items?company_id={company_id}").json()
    assert item["id"] not in [i["id"] for i in items]


def test_cash_item_update_404s_for_unknown_id(client, company):
    company_id = company["id"]
    r = client.patch(f"/cashflow/items/{uuid.uuid4()}?company_id={company_id}", json={"amount": 100})
    assert r.status_code == 404


def test_cash_item_delete_404s_for_unknown_id(client, company):
    company_id = company["id"]
    r = client.delete(f"/cashflow/items/{uuid.uuid4()}?company_id={company_id}")
    assert r.status_code == 404


def test_cash_item_scoped_to_company(client):
    r = client.post("/companies", json={"name": "CashItem Co A", "base_currency": "USD"})
    company_a = r.json()["id"]
    r = client.post("/companies", json={"name": "CashItem Co B", "base_currency": "USD"})
    company_b = r.json()["id"]

    item = _create_item(client, company_a)

    r = client.patch(f"/cashflow/items/{item['id']}?company_id={company_b}", json={"amount": 999})
    assert r.status_code == 404  # can't touch another company's item


def test_cash_item_mutations_are_audited(client, company):
    company_id = company["id"]
    item = _create_item(client, company_id)
    client.patch(f"/cashflow/items/{item['id']}?company_id={company_id}", json={"amount": 600})
    client.delete(f"/cashflow/items/{item['id']}?company_id={company_id}")

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=cash_item").json()
    actions = [e["action"] for e in entries]
    assert actions.count("create") == 1
    assert actions.count("update") == 1
    assert actions.count("delete") == 1
