def _gl_account(client, company_id, code, category, forecast_role=None):
    payload = {"code": code, "name": code, "category": category}
    if forecast_role:
        payload["forecast_role"] = forecast_role
    r = client.post(f"/gl-accounts?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _post_cash_entry(client, company_id, cash_id, revenue_id, amount, entry_date, reference="Sale"):
    entry = client.post(
        f"/journal-entries?company_id={company_id}",
        json={
            "entry_date": entry_date,
            "reference": reference,
            "currency": "USD",
            "lines": [
                {"gl_account_id": cash_id, "debit_amount": amount, "credit_amount": 0},
                {"gl_account_id": revenue_id, "debit_amount": 0, "credit_amount": amount},
            ],
        },
    ).json()
    r = client.post(f"/journal-entries/{entry['id']}/post")
    assert r.status_code == 200, r.text
    return r.json()


def _upload_csv(client, company_id, cash_id, csv_text: str):
    return client.post(
        f"/bank-statements/upload?company_id={company_id}&cash_gl_account_id={cash_id}",
        files={"file": ("statement.csv", csv_text.encode(), "text/csv")},
    )


# --- Import + auto-match ----------------------------------------------------


def test_upload_auto_matches_a_same_day_same_amount_line(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1900", "asset")
    revenue_id = _gl_account(client, company_id, "4900", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 500, "2026-01-10")

    csv_text = "date,description,amount,reference\n2026-01-10,Customer deposit,500,DEP-1\n"
    r = _upload_csv(client, company_id, cash_id, csv_text)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows_imported"] == 1
    assert body["auto_matched"] == 1

    lines = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    assert lines[0]["matched_actual_line_id"] is not None
    assert lines[0]["match_type"] == "auto"


def test_ambiguous_duplicate_amounts_are_left_unmatched(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1901", "asset")
    revenue_id = _gl_account(client, company_id, "4901", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 300, "2026-01-05", reference="Sale A")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 300, "2026-01-06", reference="Sale B")

    csv_text = "date,description,amount\n2026-01-05,Ambiguous deposit,300\n"
    r = _upload_csv(client, company_id, cash_id, csv_text)
    body = r.json()
    assert body["auto_matched"] == 0

    lines = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    assert lines[0]["matched_actual_line_id"] is None


def test_date_tolerance_boundary(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1902", "asset")
    revenue_id = _gl_account(client, company_id, "4902", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 200, "2026-01-01")

    # exactly 5 days apart -- within tolerance, should match
    r = _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-01-06,Deposit,200\n")
    assert r.json()["auto_matched"] == 1


def test_date_beyond_tolerance_is_not_matched(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1903", "asset")
    revenue_id = _gl_account(client, company_id, "4903", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 250, "2026-01-01")

    # 7 days apart -- beyond the 5-day tolerance
    r = _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-01-08,Deposit,250\n")
    assert r.json()["auto_matched"] == 0


def test_upload_requires_required_columns(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1904", "asset")
    r = _upload_csv(client, company_id, cash_id, "date,amount\n2026-01-01,100\n")
    assert r.status_code == 422


# --- Manual match / unmatch / delete ----------------------------------------


def test_manual_match_and_unmatch_round_trip(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1905", "asset")
    revenue_id = _gl_account(client, company_id, "4905", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 900, "2026-01-01")

    # Way outside tolerance, so it won't auto-match
    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-03-01,Late deposit,900\n")
    bank_line = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()[0]
    assert bank_line["matched_actual_line_id"] is None

    unmatched_gl = client.get(f"/bank-reconciliation/unmatched-gl-lines?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    assert len(unmatched_gl) == 1
    actual_line_id = unmatched_gl[0]["actual_line_id"]

    r = client.post(f"/bank-statements/{bank_line['id']}/match?company_id={company_id}", json={"actual_line_id": actual_line_id})
    assert r.status_code == 200, r.text
    assert r.json()["match_type"] == "manual"

    r2 = client.post(f"/bank-statements/{bank_line['id']}/unmatch?company_id={company_id}")
    assert r2.status_code == 200, r2.text
    assert r2.json()["matched_actual_line_id"] is None


def test_cannot_manually_match_an_already_matched_actual_line(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1906", "asset")
    revenue_id = _gl_account(client, company_id, "4906", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 700, "2026-01-01")

    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-01-01,Deposit A,700\n")
    # first upload already auto-matched the only actual line; second bank line targeting the same actual should fail
    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-06-01,Deposit B,700\n")
    lines = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    unmatched = next(ln for ln in lines if ln["matched_actual_line_id"] is None)

    unmatched_gl = client.get(f"/bank-reconciliation/unmatched-gl-lines?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    assert unmatched_gl == []  # the only actual line is already matched

    r = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    matched_actual_id = next(ln["matched_actual_line_id"] for ln in r if ln["matched_actual_line_id"])
    resp = client.post(f"/bank-statements/{unmatched['id']}/match?company_id={company_id}", json={"actual_line_id": matched_actual_id})
    assert resp.status_code == 422


def test_delete_unmatched_line_succeeds_matched_line_rejected(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1907", "asset")
    revenue_id = _gl_account(client, company_id, "4907", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 150, "2026-01-01")

    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-01-01,Matched deposit,150\n2026-09-01,Stray line,999\n")
    lines = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()
    matched_line = next(ln for ln in lines if ln["matched_actual_line_id"] is not None)
    unmatched_line = next(ln for ln in lines if ln["matched_actual_line_id"] is None)

    r = client.delete(f"/bank-statements/{unmatched_line['id']}?company_id={company_id}")
    assert r.status_code == 204

    r2 = client.delete(f"/bank-statements/{matched_line['id']}?company_id={company_id}")
    assert r2.status_code == 409


# --- Reconciliation summary --------------------------------------------------


def test_reconciliation_summary_proves_adjusted_balances_match(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1908", "asset")
    revenue_id = _gl_account(client, company_id, "4908", "revenue")

    # Matched: Dr Cash 800 on Jan 5, appears on the bank statement the same day
    _post_cash_entry(client, company_id, cash_id, revenue_id, 800, "2026-01-05", reference="Matched sale")
    # Outstanding: Dr Cash 100 on Jan 28, a deposit not yet reflected on the bank statement
    _post_cash_entry(client, company_id, cash_id, revenue_id, 100, "2026-01-28", reference="Deposit in transit")

    csv_text = "date,description,amount\n2026-01-05,Customer payment,800\n2026-01-06,Bank fee,-20\n"
    _upload_csv(client, company_id, cash_id, csv_text)

    # book_balance = 800 + 100 = 900; unmatched bank (-20 fee) + unmatched GL (100 deposit in transit)
    # adjusted_book = 900 + (-20) = 880; adjusted_bank = bank_ending(780) + 100 = 880 -> reconciled
    r = client.get(f"/bank-reconciliation/summary?company_id={company_id}&cash_gl_account_id={cash_id}&as_of=2026-01-31&bank_statement_ending_balance=780")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["book_balance"] == 900.0
    assert body["unmatched_bank_lines_total"] == -20.0
    assert body["unmatched_gl_lines_total"] == 100.0
    assert body["adjusted_book_balance"] == 880.0
    assert body["adjusted_bank_balance"] == 880.0
    assert body["is_reconciled"] is True


def test_reconciliation_summary_flags_a_real_mismatch(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1909", "asset")
    revenue_id = _gl_account(client, company_id, "4909", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 500, "2026-01-05")
    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-01-05,Customer payment,500\n")

    r = client.get(f"/bank-reconciliation/summary?company_id={company_id}&cash_gl_account_id={cash_id}&as_of=2026-01-31&bank_statement_ending_balance=1")
    assert r.status_code == 200, r.text
    assert r.json()["is_reconciled"] is False


def test_bank_reconciliation_mutations_are_audited(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1910", "asset")
    revenue_id = _gl_account(client, company_id, "4910", "revenue")
    _post_cash_entry(client, company_id, cash_id, revenue_id, 600, "2026-01-01")
    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-01-01,Deposit,600\n")

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=bank_statement").json()
    assert any(e["action"] == "import" for e in entries)


def test_bank_statement_rejects_cross_company_manual_match(client, company):
    company_id = company["id"]
    other = client.post("/companies", json={"name": "Other BankRec Co", "base_currency": "USD"}).json()
    other_cash = _gl_account(client, other["id"], "1911", "asset")
    other_revenue = _gl_account(client, other["id"], "4911", "revenue")
    other_entry = _post_cash_entry(client, other["id"], other_cash, other_revenue, 300, "2026-01-01")

    cash_id = _gl_account(client, company_id, "1912", "asset")
    _upload_csv(client, company_id, cash_id, "date,description,amount\n2026-06-01,Odd deposit,300\n")
    bank_line = client.get(f"/bank-statements?company_id={company_id}&cash_gl_account_id={cash_id}").json()[0]

    actuals = client.get(f"/actuals?company_id={other['id']}").json()
    other_actual_id = next(a["id"] for a in actuals if a["gl_account_id"] == other_cash)

    r = client.post(f"/bank-statements/{bank_line['id']}/match?company_id={company_id}", json={"actual_line_id": other_actual_id})
    assert r.status_code == 422
    assert other_entry["status"] == "posted"
