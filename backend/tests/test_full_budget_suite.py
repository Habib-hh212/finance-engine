def _make_gl_account(client, company_id, code="6000", category="expense"):
    r = client.post(
        f"/gl-accounts?company_id={company_id}",
        json={"code": code, "name": "Test Account", "category": category},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_zero_based_budget_requires_justification_to_submit(client, company):
    company_id = company["id"]
    gl_account = _make_gl_account(client, company_id, code="6100")

    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 ZBB", "type": "zero_based", "fiscal_year": 2026, "currency": "USD"},
    )
    assert r.status_code == 200, r.text
    budget = r.json()

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[{"gl_account_id": gl_account["id"], "period": "2026-01-01", "amount": 1000}],
    )
    assert r.status_code == 200, r.text

    r = client.post(f"/budgets/{budget['id']}/submit")
    assert r.status_code == 409
    assert "justification" in r.json()["detail"]

    # add justification via a fresh line replacing intent isn't supported; instead
    # create a new budget line set with justification to prove the happy path
    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 ZBB v2", "type": "zero_based", "fiscal_year": 2026, "currency": "USD"},
    )
    budget2 = r.json()
    r = client.post(
        f"/budgets/{budget2['id']}/lines",
        json=[
            {
                "gl_account_id": gl_account["id"],
                "period": "2026-01-01",
                "amount": 1000,
                "justification": "Required headcount training",
            }
        ],
    )
    assert r.status_code == 200, r.text
    r = client.post(f"/budgets/{budget2['id']}/submit")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_manager"


def test_flexible_budget_variance_decomposes_spending_and_volume(client, company):
    company_id = company["id"]
    gl_account = _make_gl_account(client, company_id, code="6200")

    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 Flexible", "type": "flexible", "fiscal_year": 2026, "currency": "USD"},
    )
    assert r.status_code == 200, r.text
    budget = r.json()

    # fixed 1000 + 10/unit variable, budgeted implicitly for some baseline volume
    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[
            {
                "gl_account_id": gl_account["id"],
                "period": "2026-01-01",
                "amount": 1000,
                "variable_rate_per_unit": 10,
            }
        ],
    )
    assert r.status_code == 200, r.text

    # actual: 120 units produced (vs. whatever was planned), actual cost 2500
    r = client.post(
        f"/actuals?company_id={company_id}",
        json={
            "gl_account_id": gl_account["id"],
            "period": "2026-01-01",
            "amount": 2500,
            "actual_quantity": 120,
        },
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/budgets/{budget['id']}/flexible-variance")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    # flexed = 1000 + 10*120 = 2200
    assert row["flexed_amount"] == 2200
    assert row["static_amount"] == 1000
    assert row["actual_amount"] == 2500
    assert row["spending_variance"] == 300  # 2500 - 2200: overspent relative to activity level
    assert row["volume_variance"] == 1200  # 2200 - 1000: activity itself drove cost up
    assert row["total_variance"] == 1500  # 2500 - 1000


def test_flexible_variance_rejected_for_non_flexible_budget(client, company):
    company_id = company["id"]
    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 Revenue", "type": "revenue", "fiscal_year": 2026, "currency": "USD"},
    )
    budget = r.json()
    r = client.get(f"/budgets/{budget['id']}/flexible-variance")
    assert r.status_code == 409


def test_rolling_budget_roll_forward_keeps_fixed_window(client, company):
    company_id = company["id"]
    gl_account = _make_gl_account(client, company_id, code="6300")

    r = client.post(
        f"/budgets?company_id={company_id}",
        json={
            "name": "Rolling 3mo",
            "type": "rolling",
            "fiscal_year": 2026,
            "currency": "USD",
            "rolling_window_months": 3,
        },
    )
    assert r.status_code == 200, r.text
    budget = r.json()
    assert budget["rolling_window_months"] == 3

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[
            {"gl_account_id": gl_account["id"], "period": "2026-01-01", "amount": 100},
            {"gl_account_id": gl_account["id"], "period": "2026-02-01", "amount": 110},
            {"gl_account_id": gl_account["id"], "period": "2026-03-01", "amount": 120},
        ],
    )
    assert r.status_code == 200, r.text

    r = client.post(f"/budgets/{budget['id']}/roll-forward")
    assert r.status_code == 200, r.text

    detail = client.get(f"/budgets/{budget['id']}").json()
    periods = sorted({line["period"] for line in detail["lines"]})
    assert periods == ["2026-02-01", "2026-03-01", "2026-04-01"]
    # the new period's line was copied from the latest existing period (120)
    new_line = next(line for line in detail["lines"] if line["period"] == "2026-04-01")
    assert new_line["amount"] == 120


def test_rolling_default_window_is_twelve_months_when_unspecified(client, company):
    company_id = company["id"]
    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "Rolling default", "type": "rolling", "fiscal_year": 2026, "currency": "USD"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["rolling_window_months"] == 12


def test_capital_budget_appraisal_computes_payback_and_roi(client, company):
    company_id = company["id"]
    gl_account = _make_gl_account(client, company_id, code="1600", category="asset")

    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "New Machine", "type": "capital", "fiscal_year": 2026, "currency": "USD"},
    )
    assert r.status_code == 200, r.text
    budget = r.json()

    r = client.post(
        f"/budgets/{budget['id']}/lines",
        json=[
            {
                "gl_account_id": gl_account["id"],
                "period": "2026-01-01",
                "amount": 10000,
                "useful_life_years": 5,
                "annual_cash_flow": 2500,
            }
        ],
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/budgets/{budget['id']}/capital-appraisal")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["payback_period_years"] == 4.0  # 10000 / 2500
    assert row["total_cash_flow"] == 12500  # 2500 * 5
    assert row["net_gain"] == 2500  # 12500 - 10000
    assert row["roi_pct"] == 25.0  # 2500 / 10000 * 100


def test_capital_appraisal_rejected_for_non_capital_budget(client, company):
    company_id = company["id"]
    r = client.post(
        f"/budgets?company_id={company_id}",
        json={"name": "FY26 Expense", "type": "expense", "fiscal_year": 2026, "currency": "USD"},
    )
    budget = r.json()
    r = client.get(f"/budgets/{budget['id']}/capital-appraisal")
    assert r.status_code == 409
