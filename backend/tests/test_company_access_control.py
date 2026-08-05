import itertools

from fastapi.testclient import TestClient

from app.main import app

_intruder_seq = itertools.count()


def _second_user_client() -> TestClient:
    """A fresh, independent client/user -- deliberately not the shared
    `client` fixture, since that's the company owner in these tests."""
    c = TestClient(app)
    c.__enter__()
    email = f"intruder{next(_intruder_seq)}@example.com"
    r = c.post("/auth/register", json={"email": email, "password": "hunter22222", "name": "Intruder"})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return c


def test_stranger_cannot_list_owners_company_in_their_own_list(client, company):
    stranger = _second_user_client()
    r = stranger.get("/companies")
    assert r.status_code == 200
    assert all(c["id"] != company["id"] for c in r.json())


def test_stranger_gets_403_on_direct_company_id_endpoints(client, company):
    stranger = _second_user_client()
    company_id = company["id"]

    for path in [
        f"/gl-accounts?company_id={company_id}",
        f"/journal-entries?company_id={company_id}",
        f"/budgets?company_id={company_id}",
        f"/reports/balance-sheet?company_id={company_id}&as_of=2026-01-01",
        f"/assets?company_id={company_id}",
        f"/scenarios?company_id={company_id}",
    ]:
        r = stranger.get(path)
        assert r.status_code == 403, f"{path} -> {r.status_code}: {r.text}"


def test_owner_still_has_access_to_their_own_company(client, company):
    r = client.get(f"/gl-accounts?company_id={company['id']}")
    assert r.status_code == 200


def test_stranger_cannot_read_or_act_on_owners_nested_resources(client, company):
    company_id = company["id"]

    gl = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "1000", "name": "Cash", "category": "asset"}).json()
    gl2 = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "4000", "name": "Revenue", "category": "revenue"}).json()

    entry = client.post(
        f"/journal-entries?company_id={company_id}",
        json={
            "entry_date": "2026-01-05",
            "lines": [
                {"gl_account_id": gl["id"], "debit_amount": 100, "credit_amount": 0},
                {"gl_account_id": gl2["id"], "debit_amount": 0, "credit_amount": 100},
            ],
        },
    ).json()

    budget = client.post(
        f"/budgets?company_id={company_id}", json={"name": "FY26 Ops", "type": "revenue", "fiscal_year": 2026, "currency": "USD"}
    ).json()

    stranger = _second_user_client()

    r = stranger.post(f"/journal-entries/{entry['id']}/post")
    assert r.status_code == 403, r.text

    r = stranger.delete(f"/journal-entries/{entry['id']}")
    assert r.status_code == 403, r.text

    r = stranger.get(f"/budgets/{budget['id']}")
    assert r.status_code == 403, r.text

    r = stranger.post(f"/budgets/{budget['id']}/submit")
    assert r.status_code == 403, r.text

    r = stranger.patch(f"/gl-accounts/{gl['id']}", json={"forecast_role": "cash"})
    assert r.status_code == 403, r.text

    # The owner, meanwhile, isn't blocked from their own resources.
    r = client.post(f"/journal-entries/{entry['id']}/post")
    assert r.status_code == 200, r.text
