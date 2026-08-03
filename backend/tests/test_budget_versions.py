def _make_budget_with_line(client, company, amount=50000):
    company_id = company["id"]
    r = client.post(
        f"/gl-accounts?company_id={company_id}",
        json={"code": "4100", "name": "Consulting Revenue", "category": "revenue"},
    )
    assert r.status_code == 200, r.text
    gl_account = r.json()

    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 Versioned Budget", "type": "revenue", "fiscal_year": 2026, "currency": "USD"},
    )
    assert r.status_code == 200, r.text
    budget = r.json()

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_account["id"], "period": "2026-01-01", "amount": amount}],
    )
    assert r.status_code == 200, r.text
    line = r.json()[0]
    return budget, gl_account, line


def test_update_line_only_while_draft(client, company):
    budget, _gl, line = _make_budget_with_line(client, company)

    r = client.patch(f"/budgets/{budget['id']}/lines/{line['id']}", json={"amount": 60000})
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 60000

    client.post(f"/budgets/{budget['id']}/submit")
    r = client.patch(f"/budgets/{budget['id']}/lines/{line['id']}", json={"amount": 70000})
    assert r.status_code == 409


def test_delete_line_only_while_draft(client, company):
    budget, gl_account, line = _make_budget_with_line(client, company)

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_account["id"], "period": "2026-02-01", "amount": 1000}],
    )
    second_line = r.json()[0]

    r = client.delete(f"/budgets/{budget['id']}/lines/{line['id']}")
    assert r.status_code == 204

    detail = client.get(f"/budgets/{budget['id']}").json()
    assert [line["id"] for line in detail["lines"]] == [second_line["id"]]

    client.post(f"/budgets/{budget['id']}/submit")
    r = client.delete(f"/budgets/{budget['id']}/lines/{second_line['id']}")
    assert r.status_code == 409


def test_version_snapshot_created_on_each_submit(client, company):
    budget, gl_account, line = _make_budget_with_line(client, company, amount=50000)
    budget_id = budget["id"]

    client.post(f"/budgets/{budget_id}/submit")
    versions = client.get(f"/budgets/{budget_id}/versions").json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["lines_snapshot"] == [
        {
            "gl_account_id": gl_account["id"],
            "period": "2026-01-01",
            "amount": 50000.0,
            "currency": "USD",
            "justification": None,
            "variable_rate_per_unit": None,
            "useful_life_years": None,
            "annual_cash_flow": None,
        }
    ]

    client.post(f"/budgets/{budget_id}/reject", json={"actor_name": "Manager Mo", "comment": "too high"})
    client.patch(f"/budgets/{budget_id}/lines/{line['id']}", json={"amount": 30000})
    client.post(f"/budgets/{budget_id}/submit")

    versions = client.get(f"/budgets/{budget_id}/versions").json()
    assert len(versions) == 2
    assert versions[1]["version_number"] == 2
    assert versions[1]["lines_snapshot"][0]["amount"] == 30000.0
    # the first version's snapshot is untouched by the later edit
    assert versions[0]["lines_snapshot"][0]["amount"] == 50000.0


def test_versions_for_budget_with_no_submissions_yet(client, company):
    budget, _gl, _line = _make_budget_with_line(client, company)
    versions = client.get(f"/budgets/{budget['id']}/versions").json()
    assert versions == []
