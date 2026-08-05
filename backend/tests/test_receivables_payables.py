def _gl_account(client, company_id, code, category, forecast_role=None):
    payload = {"code": code, "name": code, "category": category}
    if forecast_role:
        payload["forecast_role"] = forecast_role
    r = client.post(f"/gl-accounts?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _customer(client, company_id, name="Acme Co"):
    r = client.post(f"/customers?company_id={company_id}", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _vendor(client, company_id, name="Supplier Co"):
    r = client.post(f"/vendors?company_id={company_id}", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["id"]


# --- Customer invoices ------------------------------------------------------


def test_invoice_posts_a_balanced_journal_entry(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1200", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4700", "revenue")
    customer_id = _customer(client, company_id, "Invoice Test Co")

    r = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INV-1", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 1000},
    )
    assert r.status_code == 200, r.text
    invoice = r.json()
    assert invoice["amount"] == 1000.0
    assert invoice["status"] == "open"
    assert invoice["remaining_balance"] == 1000.0

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Invoice INV-1")
    assert je["status"] == "posted"
    total_debit = sum(ln["debit_amount"] for ln in je["lines"])
    total_credit = sum(ln["credit_amount"] for ln in je["lines"])
    assert total_debit == total_credit == 1000.0


def test_invoice_with_tax_code_computes_gross_amount(client, company):
    company_id = company["id"]
    ar_id = _gl_account(client, company_id, "1201", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4701", "revenue")
    vat_payable_id = _gl_account(client, company_id, "2701", "liability")
    customer_id = _customer(client, company_id, "Tax Invoice Co")

    tax_code = client.post(
        f"/tax-codes?company_id={company_id}",
        json={"country": "UK", "code": "VAT-20-INV", "name": "VAT", "tax_type": "vat", "rate_pct": 20, "direction": "output", "gl_account_id": vat_payable_id},
    ).json()

    r = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "INV-2",
            "invoice_date": "2026-01-10",
            "due_date": "2026-02-09",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 1000,
            "tax_code_id": tax_code["id"],
        },
    )
    invoice = r.json()
    assert invoice["amount"] == 1200.0  # 1000 net + 200 VAT

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Invoice INV-2")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {(ar_id, 1200.0, 0.0), (revenue_id, 0.0, 1000.0), (vat_payable_id, 0.0, 200.0)}


def test_invoice_requires_ar_account_tagged(client, company):
    company_id = company["id"]
    revenue_id = _gl_account(client, company_id, "4702", "revenue")
    customer_id = _customer(client, company_id, "No AR Co")
    r = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INV-3", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 500},
    )
    assert r.status_code == 422
    assert "accounts receivable" in r.json()["detail"].lower()


# --- Receipts + application --------------------------------------------------


def test_receipt_applied_at_full_amount_marks_invoice_paid(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1210", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4710", "revenue")
    cash_id = _gl_account(client, company_id, "1010", "asset")
    customer_id = _customer(client, company_id, "Full Pay Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INV-10", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 800},
    ).json()
    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_id, "receipt_date": "2026-01-20", "cash_gl_account_id": cash_id, "amount": 800},
    ).json()
    assert receipt["unapplied_balance"] == 800.0

    r = client.post(
        f"/customer-receipts/apply?company_id={company_id}",
        json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 800, "applied_date": "2026-01-20"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paid"
    assert r.json()["remaining_balance"] == 0.0

    receipts = client.get(f"/customer-receipts?company_id={company_id}").json()
    assert next(rr for rr in receipts if rr["id"] == receipt["id"])["unapplied_balance"] == 0.0


def test_partial_receipt_application_marks_invoice_partially_paid(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1211", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4711", "revenue")
    cash_id = _gl_account(client, company_id, "1011", "asset")
    customer_id = _customer(client, company_id, "Partial Pay Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INV-11", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 1000},
    ).json()
    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_id, "receipt_date": "2026-01-20", "cash_gl_account_id": cash_id, "amount": 400},
    ).json()
    r = client.post(
        f"/customer-receipts/apply?company_id={company_id}",
        json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 400, "applied_date": "2026-01-20"},
    )
    assert r.json()["status"] == "partially_paid"
    assert r.json()["remaining_balance"] == 600.0


def test_down_payment_received_before_invoice_can_be_applied_later(client, company):
    """A receipt with no invoice at all yet -- the down-payment case -- then
    applied once a real invoice shows up. No separate down-payment G/L
    account is needed: it's just an unapplied credit on the AR control
    account until matched, per app/models/receivables_payables.py."""
    company_id = company["id"]
    _gl_account(client, company_id, "1212", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4712", "revenue")
    cash_id = _gl_account(client, company_id, "1012", "asset")
    customer_id = _customer(client, company_id, "Down Payment Co")

    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_id, "receipt_date": "2026-01-01", "cash_gl_account_id": cash_id, "amount": 300, "reference": "Deposit"},
    ).json()
    assert receipt["unapplied_balance"] == 300.0

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INV-12", "invoice_date": "2026-01-15", "due_date": "2026-02-14", "revenue_gl_account_id": revenue_id, "net_amount": 300},
    ).json()

    r = client.post(
        f"/customer-receipts/apply?company_id={company_id}",
        json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 300, "applied_date": "2026-01-15"},
    )
    assert r.json()["status"] == "paid"


def test_cannot_apply_more_than_unapplied_receipt_balance(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1213", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4713", "revenue")
    cash_id = _gl_account(client, company_id, "1013", "asset")
    customer_id = _customer(client, company_id, "Overapply Co")
    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INV-13", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 1000},
    ).json()
    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_id, "receipt_date": "2026-01-20", "cash_gl_account_id": cash_id, "amount": 100},
    ).json()
    r = client.post(
        f"/customer-receipts/apply?company_id={company_id}",
        json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 500, "applied_date": "2026-01-20"},
    )
    assert r.status_code == 422


def test_cannot_apply_receipt_to_a_different_customers_invoice(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1214", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4714", "revenue")
    cash_id = _gl_account(client, company_id, "1014", "asset")
    customer_a = _customer(client, company_id, "Customer A")
    customer_b = _customer(client, company_id, "Customer B")
    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_a, "invoice_number": "INV-14", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 500},
    ).json()
    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_b, "receipt_date": "2026-01-20", "cash_gl_account_id": cash_id, "amount": 500},
    ).json()
    r = client.post(
        f"/customer-receipts/apply?company_id={company_id}",
        json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 500, "applied_date": "2026-01-20"},
    )
    assert r.status_code == 422


# --- Vendor bills / payments (mirror) ---------------------------------------


def test_vendor_bill_and_payment_mirror_the_customer_side(client, company):
    company_id = company["id"]
    ap_id = _gl_account(client, company_id, "2100", "liability", forecast_role="accounts_payable")
    expense_id = _gl_account(client, company_id, "6700", "expense")
    cash_id = _gl_account(client, company_id, "1015", "asset")
    vendor_id = _vendor(client, company_id, "Mirror Vendor")

    bill = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={"vendor_id": vendor_id, "bill_number": "BILL-1", "bill_date": "2026-01-05", "due_date": "2026-02-04", "expense_gl_account_id": expense_id, "net_amount": 700},
    ).json()
    assert bill["amount"] == 700.0
    assert bill["status"] == "open"

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Bill BILL-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {(expense_id, 700.0, 0.0), (ap_id, 0.0, 700.0)}

    payment = client.post(
        f"/vendor-payments?company_id={company_id}",
        json={"vendor_id": vendor_id, "payment_date": "2026-01-25", "cash_gl_account_id": cash_id, "amount": 700},
    ).json()
    r = client.post(
        f"/vendor-payments/apply?company_id={company_id}",
        json={"payment_id": payment["id"], "bill_id": bill["id"], "amount": 700, "applied_date": "2026-01-25"},
    )
    assert r.json()["status"] == "paid"
    assert r.json()["remaining_balance"] == 0.0


def test_vendor_bill_with_input_tax_code(client, company):
    company_id = company["id"]
    ap_id = _gl_account(client, company_id, "2101", "liability", forecast_role="accounts_payable")
    expense_id = _gl_account(client, company_id, "6701", "expense")
    vat_recoverable_id = _gl_account(client, company_id, "1310", "asset")
    vendor_id = _vendor(client, company_id, "Tax Bill Vendor")

    tax_code = client.post(
        f"/tax-codes?company_id={company_id}",
        json={"country": "UK", "code": "VAT-20-BILL", "name": "VAT", "tax_type": "vat", "rate_pct": 20, "direction": "input", "gl_account_id": vat_recoverable_id},
    ).json()

    bill = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={
            "vendor_id": vendor_id,
            "bill_number": "BILL-2",
            "bill_date": "2026-01-05",
            "due_date": "2026-02-04",
            "expense_gl_account_id": expense_id,
            "net_amount": 500,
            "tax_code_id": tax_code["id"],
        },
    ).json()
    assert bill["amount"] == 600.0  # 500 net + 100 input VAT

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Bill BILL-2")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {(expense_id, 500.0, 0.0), (vat_recoverable_id, 100.0, 0.0), (ap_id, 0.0, 600.0)}


# --- Aging -------------------------------------------------------------------


def test_ar_aging_buckets_by_days_overdue(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1220", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4720", "revenue")
    customer_id = _customer(client, company_id, "Aging Co")

    client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "AGE-1", "invoice_date": "2026-01-01", "due_date": "2026-01-31", "revenue_gl_account_id": revenue_id, "net_amount": 500},
    )
    client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "AGE-2", "invoice_date": "2026-01-01", "due_date": "2026-03-01", "revenue_gl_account_id": revenue_id, "net_amount": 200},
    )

    r = client.get(f"/reports/ar-aging?company_id={company_id}&as_of=2026-02-15")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_remaining"] == 700.0
    row1 = next(row for row in body["rows"] if row["number"] == "AGE-1")
    assert row1["days_overdue"] == 15  # 2026-02-15 - 2026-01-31
    assert row1["bucket"] == "1-30"
    row2 = next(row for row in body["rows"] if row["number"] == "AGE-2")
    assert row2["bucket"] == "current"  # due 2026-03-01, not yet due


def test_ar_aging_excludes_fully_paid_invoices(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1221", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4721", "revenue")
    cash_id = _gl_account(client, company_id, "1016", "asset")
    customer_id = _customer(client, company_id, "Paid Off Co")
    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "PAIDOFF-1", "invoice_date": "2026-01-01", "due_date": "2026-01-15", "revenue_gl_account_id": revenue_id, "net_amount": 100},
    ).json()
    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_id, "receipt_date": "2026-01-10", "cash_gl_account_id": cash_id, "amount": 100},
    ).json()
    client.post(f"/customer-receipts/apply?company_id={company_id}", json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 100, "applied_date": "2026-01-10"})

    r = client.get(f"/reports/ar-aging?company_id={company_id}&as_of=2026-02-15")
    assert not any(row["number"] == "PAIDOFF-1" for row in r.json()["rows"])


def test_ap_aging_buckets_by_days_overdue(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "2110", "liability", forecast_role="accounts_payable")
    expense_id = _gl_account(client, company_id, "6710", "expense")
    vendor_id = _vendor(client, company_id, "AP Aging Vendor")

    client.post(
        f"/vendor-bills?company_id={company_id}",
        json={"vendor_id": vendor_id, "bill_number": "APAGE-1", "bill_date": "2025-10-01", "due_date": "2025-10-01", "expense_gl_account_id": expense_id, "net_amount": 400},
    )
    r = client.get(f"/reports/ap-aging?company_id={company_id}&as_of=2026-02-15")
    assert r.status_code == 200, r.text
    row = next(row for row in r.json()["rows"] if row["number"] == "APAGE-1")
    assert row["bucket"] == "90+"


# --- Integration with Income Statement / Balance Sheet -----------------------


def test_invoices_and_bills_flow_into_income_statement_and_balance_sheet(client, company):
    company_id = company["id"]
    ar_id = _gl_account(client, company_id, "1230", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4730", "revenue")
    ap_id = _gl_account(client, company_id, "2120", "liability", forecast_role="accounts_payable")
    expense_id = _gl_account(client, company_id, "6720", "expense")
    customer_id = _customer(client, company_id, "Integration Customer")
    vendor_id = _vendor(client, company_id, "Integration Vendor")

    client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "INT-1", "invoice_date": "2026-03-10", "due_date": "2026-04-09", "revenue_gl_account_id": revenue_id, "net_amount": 900},
    )
    client.post(
        f"/vendor-bills?company_id={company_id}",
        json={"vendor_id": vendor_id, "bill_number": "INT-B1", "bill_date": "2026-03-12", "due_date": "2026-04-11", "expense_gl_account_id": expense_id, "net_amount": 300},
    )

    income = client.get(f"/reports/income-statement?company_id={company_id}&start_period=2026-03-01&end_period=2026-03-01").json()
    revenue_line = next(line for line in income["revenue_lines"] if line["gl_account_id"] == revenue_id)
    expense_line = next(line for line in income["expense_lines"] if line["gl_account_id"] == expense_id)
    assert revenue_line["amount"] == 900.0
    assert expense_line["amount"] == 300.0
    assert income["net_profit"] == 600.0

    balance = client.get(f"/reports/balance-sheet?company_id={company_id}&as_of=2026-03-31").json()
    ar_line = next(line for line in balance["asset_lines"] if line["gl_account_id"] == ar_id)
    ap_line = next(line for line in balance["liability_lines"] if line["gl_account_id"] == ap_id)
    assert ar_line["amount"] == 900.0
    assert ap_line["amount"] == 300.0


def test_arap_mutations_are_audited(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1240", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4740", "revenue")
    cash_id = _gl_account(client, company_id, "1017", "asset")
    customer_id = _customer(client, company_id, "Audit AR Co")
    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={"customer_id": customer_id, "invoice_number": "AUDIT-1", "invoice_date": "2026-01-10", "due_date": "2026-02-09", "revenue_gl_account_id": revenue_id, "net_amount": 100},
    ).json()
    receipt = client.post(
        f"/customer-receipts?company_id={company_id}",
        json={"customer_id": customer_id, "receipt_date": "2026-01-15", "cash_gl_account_id": cash_id, "amount": 100},
    ).json()
    client.post(f"/customer-receipts/apply?company_id={company_id}", json={"receipt_id": receipt["id"], "invoice_id": invoice["id"], "amount": 100, "applied_date": "2026-01-15"})

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=customer_invoice").json()
    assert any(e["action"] == "create" for e in entries)
    receipt_entries = client.get(f"/audit-log?company_id={company_id}&entity_type=customer_receipt").json()
    actions = [e["action"] for e in receipt_entries]
    assert "create" in actions
    assert "apply" in actions
