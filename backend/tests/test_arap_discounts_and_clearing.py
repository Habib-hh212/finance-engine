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


# --- Customer invoice discount terms ----------------------------------------


def test_invoice_stores_discount_terms(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1400", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4900", "revenue")
    customer_id = _customer(client, company_id, "Discount Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "DISC-1",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 1000,
            "discount_pct": 2,
            "discount_days": 10,
        },
    ).json()
    assert invoice["discount_pct"] == 2.0
    assert invoice["discount_days"] == 10
    assert invoice["discount_taken_amount"] is None


def test_take_customer_invoice_discount_within_window(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1401", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4901", "revenue")
    discount_id = _gl_account(client, company_id, "5900", "expense", forecast_role="sales_discount")
    customer_id = _customer(client, company_id, "Discount Co 2")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "DISC-2",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 1000,
            "discount_pct": 2,
            "discount_days": 10,
        },
    ).json()

    r = client.post(f"/customer-invoices/{invoice['id']}/discount?company_id={company_id}", json={"as_of_date": "2026-01-05"})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["discount_taken_amount"] == 20.0  # 2% of 1000
    assert updated["remaining_balance"] == 980.0
    assert updated["status"] == "partially_paid"

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Discount on invoice DISC-2")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    ar_id = client.get(f"/gl-accounts?company_id={company_id}").json()[0]["id"]
    assert (discount_id, 20.0, 0.0) in lines
    assert (ar_id, 0.0, 20.0) in lines


def test_take_customer_invoice_discount_outside_window_errors(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1402", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4902", "revenue")
    _gl_account(client, company_id, "5901", "expense", forecast_role="sales_discount")
    customer_id = _customer(client, company_id, "Discount Co 3")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "DISC-3",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 1000,
            "discount_pct": 2,
            "discount_days": 10,
        },
    ).json()

    r = client.post(f"/customer-invoices/{invoice['id']}/discount?company_id={company_id}", json={"as_of_date": "2026-01-20"})
    assert r.status_code == 422
    assert "window" in r.json()["detail"]


def test_take_customer_invoice_discount_twice_errors(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1403", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4903", "revenue")
    _gl_account(client, company_id, "5902", "expense", forecast_role="sales_discount")
    customer_id = _customer(client, company_id, "Discount Co 4")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "DISC-4",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 1000,
            "discount_pct": 2,
            "discount_days": 10,
        },
    ).json()

    client.post(f"/customer-invoices/{invoice['id']}/discount?company_id={company_id}", json={"as_of_date": "2026-01-05"})
    r = client.post(f"/customer-invoices/{invoice['id']}/discount?company_id={company_id}", json={"as_of_date": "2026-01-06"})
    assert r.status_code == 422
    assert "already been taken" in r.json()["detail"]


def test_clear_customer_invoice_without_discount(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1404", "asset", forecast_role="accounts_receivable")
    cash_id = _gl_account(client, company_id, "1010", "asset")
    revenue_id = _gl_account(client, company_id, "4904", "revenue")
    customer_id = _customer(client, company_id, "Clear Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "CLEAR-1",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 500,
        },
    ).json()

    r = client.post(
        f"/customer-invoices/{invoice['id']}/clear?company_id={company_id}",
        json={"cash_gl_account_id": cash_id, "cleared_date": "2026-01-15"},
    )
    assert r.status_code == 200, r.text
    cleared = r.json()
    assert cleared["status"] == "paid"
    assert cleared["remaining_balance"] == 0.0

    receipts = client.get(f"/customer-receipts?company_id={company_id}").json()
    assert any(rc["amount"] == 500.0 and rc["unapplied_balance"] == 0.0 for rc in receipts)


def test_clear_customer_invoice_with_discount(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1405", "asset", forecast_role="accounts_receivable")
    cash_id = _gl_account(client, company_id, "1011", "asset")
    revenue_id = _gl_account(client, company_id, "4905", "revenue")
    _gl_account(client, company_id, "5903", "expense", forecast_role="sales_discount")
    customer_id = _customer(client, company_id, "Clear Discount Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "CLEAR-2",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 1000,
            "discount_pct": 2,
            "discount_days": 10,
        },
    ).json()

    r = client.post(
        f"/customer-invoices/{invoice['id']}/clear?company_id={company_id}",
        json={"cash_gl_account_id": cash_id, "cleared_date": "2026-01-05", "take_discount": True},
    )
    assert r.status_code == 200, r.text
    cleared = r.json()
    assert cleared["discount_taken_amount"] == 20.0
    assert cleared["status"] == "paid"
    assert cleared["remaining_balance"] == 0.0

    receipts = client.get(f"/customer-receipts?company_id={company_id}").json()
    assert any(rc["amount"] == 980.0 for rc in receipts)  # only the net-of-discount amount was collected


# --- Vendor bill discount terms + clearing ----------------------------------


def test_clear_vendor_bill_with_discount(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "2400", "liability", forecast_role="accounts_payable")
    cash_id = _gl_account(client, company_id, "1012", "asset")
    expense_id = _gl_account(client, company_id, "6900", "expense")
    _gl_account(client, company_id, "4200", "revenue", forecast_role="purchase_discount")
    vendor_id = _vendor(client, company_id, "Discount Vendor")

    bill = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={
            "vendor_id": vendor_id,
            "bill_number": "BILLDISC-1",
            "bill_date": "2026-01-01",
            "due_date": "2026-01-31",
            "expense_gl_account_id": expense_id,
            "net_amount": 2000,
            "discount_pct": 1,
            "discount_days": 15,
        },
    ).json()
    assert bill["discount_pct"] == 1.0

    r = client.post(f"/vendor-bills/{bill['id']}/discount?company_id={company_id}", json={"as_of_date": "2026-01-10"})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["discount_taken_amount"] == 20.0  # 1% of 2000
    assert updated["remaining_balance"] == 1980.0

    r = client.post(
        f"/vendor-bills/{bill['id']}/clear?company_id={company_id}",
        json={"cash_gl_account_id": cash_id, "cleared_date": "2026-01-11"},
    )
    assert r.status_code == 200, r.text
    cleared = r.json()
    assert cleared["status"] == "paid"
    assert cleared["remaining_balance"] == 0.0

    payments = client.get(f"/vendor-payments?company_id={company_id}").json()
    assert any(p["amount"] == 1980.0 for p in payments)


def test_take_discount_without_terms_errors(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1406", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4906", "revenue")
    customer_id = _customer(client, company_id, "No Terms Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "NOTERMS-1",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 500,
        },
    ).json()

    r = client.post(f"/customer-invoices/{invoice['id']}/discount?company_id={company_id}", json={"as_of_date": "2026-01-05"})
    assert r.status_code == 422
    assert "no discount terms" in r.json()["detail"]


def test_clear_already_paid_invoice_errors(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "1407", "asset", forecast_role="accounts_receivable")
    cash_id = _gl_account(client, company_id, "1013", "asset")
    revenue_id = _gl_account(client, company_id, "4907", "revenue")
    customer_id = _customer(client, company_id, "Already Paid Co")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "PAID-1",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 300,
        },
    ).json()
    client.post(
        f"/customer-invoices/{invoice['id']}/clear?company_id={company_id}",
        json={"cash_gl_account_id": cash_id, "cleared_date": "2026-01-15"},
    )

    r = client.post(
        f"/customer-invoices/{invoice['id']}/clear?company_id={company_id}",
        json={"cash_gl_account_id": cash_id, "cleared_date": "2026-01-16"},
    )
    assert r.status_code == 422
    assert "no remaining balance" in r.json()["detail"]
