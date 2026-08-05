def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _create_entry(client, company_id, lines, entry_date="2026-01-01", reference="Test entry"):
    return client.post(
        f"/journal-entries?company_id={company_id}",
        json={"entry_date": entry_date, "reference": reference, "currency": "USD", "lines": lines},
    )


def test_balanced_entry_can_be_created_and_posted(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1000", "asset")
    revenue_id = _gl_account(client, company_id, "4000", "revenue")

    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 1000, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 1000},
        ],
    )
    assert r.status_code == 200, r.text
    entry = r.json()
    assert entry["status"] == "draft"

    r = client.post(f"/journal-entries/{entry['id']}/post")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "posted"

    # Cash (asset, debit-normal) should show as a positive $1000 actual;
    # Revenue (credit-normal) should also show as a positive $1000 actual --
    # both read as "the natural increase happened," which is what a manual
    # actuals-post would look like for the exact same real event.
    actuals = client.get(f"/actuals?company_id={company_id}").json()
    cash_actual = next(a for a in actuals if a["gl_account_id"] == cash_id)
    revenue_actual = next(a for a in actuals if a["gl_account_id"] == revenue_id)
    assert cash_actual["amount"] == 1000
    assert revenue_actual["amount"] == 1000
    assert cash_actual["journal_entry_line_id"] is not None


def test_unbalanced_entry_is_rejected(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1001", "asset")
    revenue_id = _gl_account(client, company_id, "4001", "revenue")

    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 1000, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 900},
        ],
    )
    assert r.status_code == 422
    assert "balance" in r.json()["detail"].lower()


def test_single_line_entry_is_rejected(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1002", "asset")
    r = _create_entry(client, company_id, [{"gl_account_id": cash_id, "debit_amount": 500, "credit_amount": 0}])
    assert r.status_code == 422
    assert "two lines" in r.json()["detail"].lower()


def test_line_with_both_debit_and_credit_is_rejected(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1003", "asset")
    revenue_id = _gl_account(client, company_id, "4003", "revenue")
    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 500, "credit_amount": 500},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 500},
        ],
    )
    assert r.status_code == 422
    assert "both a debit and a credit" in r.json()["detail"].lower()


def test_line_with_neither_debit_nor_credit_is_rejected(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1004", "asset")
    revenue_id = _gl_account(client, company_id, "4004", "revenue")
    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 0, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 500},
        ],
    )
    assert r.status_code == 422


def test_cannot_post_an_already_posted_entry(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1005", "asset")
    revenue_id = _gl_account(client, company_id, "4005", "revenue")
    entry = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 200, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 200},
        ],
    ).json()
    client.post(f"/journal-entries/{entry['id']}/post")
    r = client.post(f"/journal-entries/{entry['id']}/post")
    assert r.status_code == 409


def test_draft_entry_can_be_deleted(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1006", "asset")
    revenue_id = _gl_account(client, company_id, "4006", "revenue")
    entry = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 100, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 100},
        ],
    ).json()
    r = client.delete(f"/journal-entries/{entry['id']}")
    assert r.status_code == 204

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    assert entry["id"] not in [e["id"] for e in entries]


def test_posted_entry_cannot_be_deleted(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1007", "asset")
    revenue_id = _gl_account(client, company_id, "4007", "revenue")
    entry = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 100, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 100},
        ],
    ).json()
    client.post(f"/journal-entries/{entry['id']}/post")
    r = client.delete(f"/journal-entries/{entry['id']}")
    assert r.status_code == 409


def test_reversing_a_posted_entry_zeroes_out_the_actuals(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1008", "asset")
    revenue_id = _gl_account(client, company_id, "4008", "revenue")
    entry = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 500, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 500},
        ],
        entry_date="2026-02-01",
    ).json()
    client.post(f"/journal-entries/{entry['id']}/post")

    r = client.post(f"/journal-entries/{entry['id']}/reverse", json={"entry_date": "2026-02-15"})
    assert r.status_code == 200, r.text
    reversal = r.json()
    assert reversal["status"] == "posted"
    assert reversal["reverses_entry_id"] == entry["id"]

    original = client.get(f"/journal-entries?company_id={company_id}").json()
    original_status = next(e["status"] for e in original if e["id"] == entry["id"])
    assert original_status == "reversed"

    actuals = [a for a in client.get(f"/actuals?company_id={company_id}").json() if a["gl_account_id"] == cash_id]
    assert sum(a["amount"] for a in actuals) == 0  # +500 from the original, -500 from the reversal


def test_cannot_reverse_a_draft_entry(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1009", "asset")
    revenue_id = _gl_account(client, company_id, "4009", "revenue")
    entry = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 100, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 100},
        ],
    ).json()
    r = client.post(f"/journal-entries/{entry['id']}/reverse", json={"entry_date": "2026-01-05"})
    assert r.status_code == 409


def test_trial_balance_proves_debits_equal_credits(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1010", "asset")
    revenue_id = _gl_account(client, company_id, "4010", "revenue")
    expense_id = _gl_account(client, company_id, "6010", "expense")
    payable_id = _gl_account(client, company_id, "2010", "liability")

    e1 = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 2000, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 2000},
        ],
        entry_date="2026-03-01",
    ).json()
    e2 = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": expense_id, "debit_amount": 300, "credit_amount": 0},
            {"gl_account_id": payable_id, "debit_amount": 0, "credit_amount": 300},
        ],
        entry_date="2026-03-05",
    ).json()
    client.post(f"/journal-entries/{e1['id']}/post")
    client.post(f"/journal-entries/{e2['id']}/post")

    r = client.get(f"/trial-balance?company_id={company_id}&as_of=2026-03-31")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_balanced"] is True
    assert body["total_debit"] == body["total_credit"] == 2300

    cash_row = next(row for row in body["rows"] if row["gl_account_id"] == cash_id)
    assert cash_row["net_balance"] == 2000  # debit-normal, all debit
    revenue_row = next(row for row in body["rows"] if row["gl_account_id"] == revenue_id)
    assert revenue_row["net_balance"] == 2000  # credit-normal, all credit


def test_trial_balance_excludes_draft_entries(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1011", "asset")
    revenue_id = _gl_account(client, company_id, "4011", "revenue")
    _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 999, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 999},
        ],
    )  # left as draft, never posted

    r = client.get(f"/trial-balance?company_id={company_id}&as_of=2026-12-31")
    assert r.json()["rows"] == []


def test_journal_entry_rejects_account_from_another_company(client, company):
    company_id = company["id"]
    other = client.post("/companies", json={"name": "Other Co", "base_currency": "USD"}).json()
    other_gl = _gl_account(client, other["id"], "9999", "asset")
    own_revenue = _gl_account(client, company_id, "4012", "revenue")

    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": other_gl, "debit_amount": 100, "credit_amount": 0},
            {"gl_account_id": own_revenue, "debit_amount": 0, "credit_amount": 100},
        ],
    )
    assert r.status_code == 422


def test_journal_entry_mutations_are_audited(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1012", "asset")
    revenue_id = _gl_account(client, company_id, "4013", "revenue")
    entry = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 100, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 100},
        ],
    ).json()
    client.post(f"/journal-entries/{entry['id']}/post")

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=journal_entry").json()
    actions = [e["action"] for e in entries]
    assert "create" in actions
    assert "post" in actions
