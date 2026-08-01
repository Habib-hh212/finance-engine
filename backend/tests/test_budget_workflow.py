def _make_budget_with_line(client, company):
    company_id = company["id"]
    r = client.post(
        f"/gl-accounts?company_id={company_id}",
        json={"code": "4000", "name": "Sales Revenue", "category": "revenue"},
    )
    assert r.status_code == 200, r.text
    gl_account = r.json()

    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 Revenue Budget", "type": "revenue", "fiscal_year": 2026, "currency": "USD"},
    )
    assert r.status_code == 200, r.text
    budget = r.json()

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_account["id"], "period": "2026-01-01", "amount": 50000}],
    )
    assert r.status_code == 200, r.text
    return budget


def test_full_approval_chain_locks_budget(client, company):
    budget = _make_budget_with_line(client, company)
    budget_id = budget["id"]
    assert budget["status"] == "draft"

    r = client.post(f"/budgets/{budget_id}/submit")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_manager"

    r = client.post(f"/budgets/{budget_id}/approve", json={"actor_name": "Manager Mo"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_finance"

    r = client.post(f"/budgets/{budget_id}/approve", json={"actor_name": "Finance Fay"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_cfo"

    r = client.post(f"/budgets/{budget_id}/approve", json={"actor_name": "CFO Cara"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # locked: no further approvals accepted
    r = client.post(f"/budgets/{budget_id}/approve", json={"actor_name": "CFO Cara"})
    assert r.status_code == 409

    detail = client.get(f"/budgets/{budget_id}").json()
    assert [a["role"] for a in detail["approvals"]] == ["manager", "finance", "cfo"]
    assert all(a["action"] == "approved" for a in detail["approvals"])


def test_cannot_approve_before_submit(client, company):
    budget = _make_budget_with_line(client, company)
    r = client.post(f"/budgets/{budget['id']}/approve", json={"actor_name": "Manager Mo"})
    assert r.status_code == 409


def test_cannot_edit_lines_after_submit(client, company):
    budget = _make_budget_with_line(client, company)
    client.post(f"/budgets/{budget['id']}/submit")

    r = client.get(f"/gl-accounts?company_id={company['id']}")
    gl_account_id = r.json()[0]["id"]

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_account_id, "period": "2026-02-01", "amount": 1000}],
    )
    assert r.status_code == 409


def test_reject_then_resubmit_restarts_chain(client, company):
    budget = _make_budget_with_line(client, company)
    budget_id = budget["id"]

    client.post(f"/budgets/{budget_id}/submit")
    r = client.post(f"/budgets/{budget_id}/reject", json={"actor_name": "Manager Mo", "comment": "Numbers look high"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"

    # rejected budgets can be resubmitted, restarting the chain at manager
    r = client.post(f"/budgets/{budget_id}/submit")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_manager"

    detail = client.get(f"/budgets/{budget_id}").json()
    assert detail["approvals"][-1]["action"] == "rejected"
    assert detail["approvals"][-1]["comment"] == "Numbers look high"


def test_forecast_and_budget_share_the_same_company(client, company):
    # sanity check that the two modules coexist against the same company record
    r = client.get("/companies")
    assert r.status_code == 200
    assert any(c["id"] == company["id"] for c in r.json())
