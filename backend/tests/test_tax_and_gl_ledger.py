def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _tax_code(client, company_id, gl_account_id, code="VAT-OUT", country="United Kingdom", tax_type="vat", rate_pct=20, direction="output"):
    r = client.post(
        f"/tax-codes?company_id={company_id}",
        json={
            "country": country,
            "code": code,
            "name": f"{country} {code}",
            "tax_type": tax_type,
            "rate_pct": rate_pct,
            "direction": direction,
            "gl_account_id": gl_account_id,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _create_entry(client, company_id, lines, entry_date="2026-01-01", reference="Test entry"):
    return client.post(
        f"/journal-entries?company_id={company_id}",
        json={"entry_date": entry_date, "reference": reference, "currency": "USD", "lines": lines},
    )


# --- Tax code CRUD -----------------------------------------------------


def test_tax_code_can_be_created_and_listed(client, company):
    company_id = company["id"]
    tax_payable_id = _gl_account(client, company_id, "2100", "liability")
    tax_code = _tax_code(client, company_id, tax_payable_id)
    assert tax_code["rate_pct"] == 20
    assert tax_code["gl_account_code"] == "2100"
    assert tax_code["is_active"] is True

    r = client.get(f"/tax-codes?company_id={company_id}")
    assert r.status_code == 200
    assert any(tc["id"] == tax_code["id"] for tc in r.json())


def test_tax_code_rejects_unknown_tax_type_or_direction(client, company):
    company_id = company["id"]
    gl_id = _gl_account(client, company_id, "2101", "liability")
    r = client.post(
        f"/tax-codes?company_id={company_id}",
        json={"country": "India", "code": "BAD", "name": "Bad", "tax_type": "sales_tax", "rate_pct": 10, "direction": "output", "gl_account_id": gl_id},
    )
    assert r.status_code == 422


def test_tax_code_rejects_gl_account_from_another_company(client, company):
    company_id = company["id"]
    other = client.post("/companies", json={"name": "Other Co", "base_currency": "USD"}).json()
    other_gl = _gl_account(client, other["id"], "9998", "liability")
    r = client.post(
        f"/tax-codes?company_id={company_id}",
        json={"country": "India", "code": "GST-OUT", "name": "GST Out", "tax_type": "gst", "rate_pct": 18, "direction": "output", "gl_account_id": other_gl},
    )
    assert r.status_code == 422


def test_tax_code_can_be_deactivated(client, company):
    company_id = company["id"]
    gl_id = _gl_account(client, company_id, "2102", "liability")
    tax_code = _tax_code(client, company_id, gl_id, code="VAT-X")
    r = client.patch(f"/tax-codes/{tax_code['id']}?company_id={company_id}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False


# --- Tax auto-posting on journal entries --------------------------------


def test_output_tax_code_adds_a_credit_line_to_the_tax_account(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1100", "asset")
    revenue_id = _gl_account(client, company_id, "4100", "revenue")
    vat_payable_id = _gl_account(client, company_id, "2110", "liability")
    tax_code = _tax_code(client, company_id, vat_payable_id, code="VAT-OUT-20", rate_pct=20, direction="output")

    # Sale of 1000 + 20% output VAT: Dr Cash 1200 / Cr Revenue 1000 / Cr VAT Payable 200
    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 1200, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 1000, "tax_code_id": tax_code["id"]},
        ],
    )
    assert r.status_code == 200, r.text
    entry = r.json()
    assert len(entry["lines"]) == 3  # cash + revenue + auto-generated tax line

    tax_line = next(line for line in entry["lines"] if line["gl_account_id"] == vat_payable_id)
    assert tax_line["credit_amount"] == 200
    assert tax_line["debit_amount"] == 0
    assert tax_line["tax_amount"] == 200
    assert tax_line["tax_code"] == "VAT-OUT-20"

    r = client.post(f"/journal-entries/{entry['id']}/post")
    assert r.status_code == 200, r.text

    actuals = client.get(f"/actuals?company_id={company_id}").json()
    tax_actual = next(a for a in actuals if a["gl_account_id"] == vat_payable_id)
    assert tax_actual["amount"] == 200  # liability, credit-normal: +200 owed


def test_input_tax_code_adds_a_debit_line_to_the_tax_account(client, company):
    company_id = company["id"]
    expense_id = _gl_account(client, company_id, "6100", "expense")
    payable_id = _gl_account(client, company_id, "2111", "liability")
    vat_recoverable_id = _gl_account(client, company_id, "1110", "asset")
    tax_code = _tax_code(client, company_id, vat_recoverable_id, code="VAT-IN-20", rate_pct=20, direction="input")

    # Purchase of 500 + 20% input VAT: Dr Expense 500 / Dr Input VAT 100 / Cr Payable 600
    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": expense_id, "debit_amount": 500, "credit_amount": 0, "tax_code_id": tax_code["id"]},
            {"gl_account_id": payable_id, "debit_amount": 0, "credit_amount": 600},
        ],
    )
    assert r.status_code == 200, r.text
    entry = r.json()

    tax_line = next(line for line in entry["lines"] if line["gl_account_id"] == vat_recoverable_id)
    assert tax_line["debit_amount"] == 100
    assert tax_line["tax_amount"] == 100


def test_journal_entry_with_tax_code_still_enforces_balance(client, company):
    company_id = company["id"]
    expense_id = _gl_account(client, company_id, "6101", "expense")
    payable_id = _gl_account(client, company_id, "2112", "liability")
    vat_recoverable_id = _gl_account(client, company_id, "1111", "asset")
    tax_code = _tax_code(client, company_id, vat_recoverable_id, code="VAT-IN-X", rate_pct=20, direction="input")

    # Counter line doesn't include the tax amount -> out of balance (500 + 100 debit vs 500 credit)
    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": expense_id, "debit_amount": 500, "credit_amount": 0, "tax_code_id": tax_code["id"]},
            {"gl_account_id": payable_id, "debit_amount": 0, "credit_amount": 500},
        ],
    )
    assert r.status_code == 422
    assert "balance" in r.json()["detail"].lower()


def test_inactive_tax_code_is_rejected(client, company):
    company_id = company["id"]
    expense_id = _gl_account(client, company_id, "6102", "expense")
    payable_id = _gl_account(client, company_id, "2113", "liability")
    vat_id = _gl_account(client, company_id, "1112", "asset")
    tax_code = _tax_code(client, company_id, vat_id, code="VAT-INACTIVE", rate_pct=20, direction="input")
    client.patch(f"/tax-codes/{tax_code['id']}?company_id={company_id}", json={"is_active": False})

    r = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": expense_id, "debit_amount": 500, "credit_amount": 0, "tax_code_id": tax_code["id"]},
            {"gl_account_id": payable_id, "debit_amount": 0, "credit_amount": 600},
        ],
    )
    assert r.status_code == 422
    assert "inactive" in r.json()["detail"].lower()


# --- Tax report (VAT/GST return) ----------------------------------------


def test_tax_report_nets_output_against_input_tax(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1120", "asset")
    revenue_id = _gl_account(client, company_id, "4120", "revenue")
    expense_id = _gl_account(client, company_id, "6120", "expense")
    payable_id = _gl_account(client, company_id, "2120", "liability")
    vat_payable_id = _gl_account(client, company_id, "2121", "liability")
    vat_recoverable_id = _gl_account(client, company_id, "1121", "asset")

    output_code = _tax_code(client, company_id, vat_payable_id, code="OUT-20", rate_pct=20, direction="output")
    input_code = _tax_code(client, company_id, vat_recoverable_id, code="IN-20", rate_pct=20, direction="input")

    sale = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 1200, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 1000, "tax_code_id": output_code["id"]},
        ],
        entry_date="2026-04-01",
    ).json()
    purchase = _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": expense_id, "debit_amount": 500, "credit_amount": 0, "tax_code_id": input_code["id"]},
            {"gl_account_id": payable_id, "debit_amount": 0, "credit_amount": 600},
        ],
        entry_date="2026-04-10",
    ).json()
    client.post(f"/journal-entries/{sale['id']}/post")
    client.post(f"/journal-entries/{purchase['id']}/post")

    r = client.get(f"/tax-report?company_id={company_id}&start=2026-04-01&end=2026-04-30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_output_tax"] == 200
    assert body["total_input_tax"] == 100
    assert body["net_tax_payable"] == 100  # owe the tax authority 100 net

    output_row = next(row for row in body["rows"] if row["code"] == "OUT-20")
    assert output_row["taxable_base"] == 1000
    assert output_row["tax_amount"] == 200


def test_tax_report_excludes_draft_entries(client, company):
    company_id = company["id"]
    revenue_id = _gl_account(client, company_id, "4121", "revenue")
    cash_id = _gl_account(client, company_id, "1122", "asset")
    vat_payable_id = _gl_account(client, company_id, "2122", "liability")
    tax_code = _tax_code(client, company_id, vat_payable_id, code="DRAFT-VAT", rate_pct=15, direction="output")

    _create_entry(
        client,
        company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 1150, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 1000, "tax_code_id": tax_code["id"]},
        ],
        entry_date="2026-05-01",
    )  # left as draft

    r = client.get(f"/tax-report?company_id={company_id}&start=2026-05-01&end=2026-05-31")
    assert r.json()["rows"] == []


# --- GL account ledger (T-account statement) ----------------------------


def test_gl_ledger_shows_running_balance_in_date_order(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1200", "asset")
    revenue_id = _gl_account(client, company_id, "4200", "revenue")
    expense_id = _gl_account(client, company_id, "6200", "expense")

    e1 = _create_entry(
        client, company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 1000, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 1000},
        ],
        entry_date="2026-06-01",
    ).json()
    e2 = _create_entry(
        client, company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 0, "credit_amount": 300},
            {"gl_account_id": expense_id, "debit_amount": 300, "credit_amount": 0},
        ],
        entry_date="2026-06-10",
    ).json()
    client.post(f"/journal-entries/{e1['id']}/post")
    client.post(f"/journal-entries/{e2['id']}/post")

    r = client.get(f"/gl-ledger?company_id={company_id}&gl_account_id={cash_id}&start=2026-06-01&end=2026-06-30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["opening_balance"] == 0
    assert len(body["lines"]) == 2
    assert body["lines"][0]["running_balance"] == 1000
    assert body["lines"][1]["running_balance"] == 700
    assert body["closing_balance"] == 700


def test_gl_ledger_opening_balance_carries_forward_prior_activity(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1201", "asset")
    revenue_id = _gl_account(client, company_id, "4201", "revenue")

    e1 = _create_entry(
        client, company_id,
        [
            {"gl_account_id": cash_id, "debit_amount": 400, "credit_amount": 0},
            {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": 400},
        ],
        entry_date="2026-07-01",
    ).json()
    client.post(f"/journal-entries/{e1['id']}/post")

    r = client.get(f"/gl-ledger?company_id={company_id}&gl_account_id={cash_id}&start=2026-07-15&end=2026-07-31")
    body = r.json()
    assert body["opening_balance"] == 400
    assert body["lines"] == []
    assert body["closing_balance"] == 400


def test_gl_ledger_rejects_account_from_another_company(client, company):
    company_id = company["id"]
    other = client.post("/companies", json={"name": "Other Co 2", "base_currency": "USD"}).json()
    other_gl = _gl_account(client, other["id"], "9997", "asset")

    r = client.get(f"/gl-ledger?company_id={company_id}&gl_account_id={other_gl}&start=2026-01-01&end=2026-12-31")
    assert r.status_code == 404


def test_tax_code_mutations_are_audited(client, company):
    company_id = company["id"]
    gl_id = _gl_account(client, company_id, "2130", "liability")
    tax_code = _tax_code(client, company_id, gl_id, code="AUDIT-VAT")
    client.patch(f"/tax-codes/{tax_code['id']}?company_id={company_id}", json={"rate_pct": 21})

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=tax_code").json()
    actions = [e["action"] for e in entries]
    assert "create" in actions
    assert "update" in actions
