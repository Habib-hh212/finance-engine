def test_gl_account_creation_is_logged(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "4900", "name": "Consulting", "category": "revenue"})
    assert r.status_code == 200, r.text

    r = client.get(f"/audit-log?company_id={company_id}")
    assert r.status_code == 200, r.text
    entries = r.json()
    matches = [e for e in entries if e["entity_type"] == "gl_account" and e["action"] == "create"]
    assert len(matches) == 1
    assert "4900" in matches[0]["summary"]
    assert matches[0]["actor_email"] == "test@example.com"


def test_actual_posting_is_logged(client, company):
    company_id = company["id"]
    gl = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6900", "name": "Travel", "category": "expense"}).json()
    r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl["id"], "period": "2026-01-01", "amount": 250})
    assert r.status_code == 200, r.text

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=actual_line").json()
    assert len(entries) == 1
    assert entries[0]["action"] == "create"
    assert "250" in entries[0]["summary"]


def test_budget_lifecycle_is_logged(client, company):
    company_id = company["id"]
    gl = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6901", "name": "Rent", "category": "expense"}).json()
    budget = client.post(
        f"/budgets?company_id={company_id}", json={"name": "Ops Budget", "type": "expense", "fiscal_year": 2026, "currency": "USD"}
    ).json()
    client.post(f"/budgets/{budget['id']}/lines", json=[{"gl_account_id": gl["id"], "period": "2026-01-01", "amount": 1000}])
    client.post(f"/budgets/{budget['id']}/submit")
    client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=budget").json()
    actions = {e["action"] for e in entries}
    assert {"create", "update", "submit", "approve"} <= actions


def test_cost_center_creation_is_logged(client, company):
    company_id = company["id"]
    r = client.post(f"/cost-centers?company_id={company_id}", json={"code": "CC-9", "name": "Support"})
    assert r.status_code == 200, r.text

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=cost_center").json()
    assert len(entries) == 1
    assert entries[0]["action"] == "create"


def test_audit_log_is_scoped_to_company(client):
    r = client.post("/companies", json={"name": "Other Co", "base_currency": "USD"})
    other_company_id = r.json()["id"]
    client.post(f"/gl-accounts?company_id={other_company_id}", json={"code": "1", "name": "X", "category": "asset"})

    r = client.post("/companies", json={"name": "Isolated Co", "base_currency": "USD"})
    isolated_company_id = r.json()["id"]

    entries = client.get(f"/audit-log?company_id={isolated_company_id}").json()
    assert entries == []


def test_audit_log_returns_newest_first(client, company):
    company_id = company["id"]
    client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6902", "name": "First", "category": "expense"})
    client.post(f"/gl-accounts?company_id={company_id}", json={"code": "6903", "name": "Second", "category": "expense"})

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=gl_account").json()
    assert len(entries) >= 2
    timestamps = [e["created_at"] for e in entries]
    assert timestamps == sorted(timestamps, reverse=True)
