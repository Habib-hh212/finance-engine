def _gl_account(client, company_id, code, category, forecast_role=None, hsn_sac_code=None):
    payload = {"code": code, "name": code, "category": category}
    if forecast_role:
        payload["forecast_role"] = forecast_role
    if hsn_sac_code:
        payload["hsn_sac_code"] = hsn_sac_code
    r = client.post(f"/gl-accounts?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _customer(client, company_id, name="Acme Co", state=None, gstin=None):
    r = client.post(f"/customers?company_id={company_id}", json={"name": name, "state": state, "gstin": gstin})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _vendor(client, company_id, name="Supplier Co", state=None, gstin=None):
    r = client.post(f"/vendors?company_id={company_id}", json={"name": name, "state": state, "gstin": gstin})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _set_home_state(client, company_id, state):
    r = client.patch(f"/companies/{company_id}", json={"home_state": state})
    assert r.status_code == 200, r.text
    return r.json()


def _gst_rate(client, company_id, cgst_id, sgst_id, igst_id, description="Standard 18%", rate_pct=18, direction="output"):
    r = client.post(
        f"/gst-rates?company_id={company_id}",
        json={
            "description": description,
            "rate_pct": rate_pct,
            "direction": direction,
            "cgst_gl_account_id": cgst_id,
            "sgst_gl_account_id": sgst_id,
            "igst_gl_account_id": igst_id,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_gst_rate_create_list_update(client, company):
    company_id = company["id"]
    cgst = _gl_account(client, company_id, "2300", "liability")
    sgst = _gl_account(client, company_id, "2301", "liability")
    igst = _gl_account(client, company_id, "2302", "liability")
    rate = _gst_rate(client, company_id, cgst, sgst, igst)
    assert rate["rate_pct"] == 18.0
    assert rate["is_active"] is True

    listed = client.get(f"/gst-rates?company_id={company_id}").json()
    assert any(r["id"] == rate["id"] for r in listed)

    r = client.patch(f"/gst-rates/{rate['id']}?company_id={company_id}", json={"rate_pct": 12, "is_active": False})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["rate_pct"] == 12.0
    assert updated["is_active"] is False


def test_intra_state_invoice_splits_cgst_and_sgst(client, company):
    company_id = company["id"]
    _set_home_state(client, company_id, "Maharashtra")
    ar_id = _gl_account(client, company_id, "1300", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4800", "revenue")
    cgst = _gl_account(client, company_id, "2310", "liability")
    sgst = _gl_account(client, company_id, "2311", "liability")
    igst = _gl_account(client, company_id, "2312", "liability")
    rate = _gst_rate(client, company_id, cgst, sgst, igst, rate_pct=18, direction="output")
    customer_id = _customer(client, company_id, "Intra State Co", state="Maharashtra")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "GST-INTRA-1",
            "invoice_date": "2026-01-10",
            "due_date": "2026-02-09",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 10000,
            "gst_rate_id": rate["id"],
        },
    ).json()
    assert invoice["cgst_amount"] == 900.0
    assert invoice["sgst_amount"] == 900.0
    assert invoice["igst_amount"] == 0.0
    assert invoice["amount"] == 11800.0

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Invoice GST-INTRA-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {
        (ar_id, 11800.0, 0.0),
        (revenue_id, 0.0, 10000.0),
        (cgst, 0.0, 900.0),
        (sgst, 0.0, 900.0),
    }
    total_debit = sum(ln["debit_amount"] for ln in je["lines"])
    total_credit = sum(ln["credit_amount"] for ln in je["lines"])
    assert total_debit == total_credit == 11800.0


def test_inter_state_invoice_uses_igst_only(client, company):
    company_id = company["id"]
    _set_home_state(client, company_id, "Maharashtra")
    ar_id = _gl_account(client, company_id, "1301", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4801", "revenue")
    cgst = _gl_account(client, company_id, "2313", "liability")
    sgst = _gl_account(client, company_id, "2314", "liability")
    igst = _gl_account(client, company_id, "2315", "liability")
    rate = _gst_rate(client, company_id, cgst, sgst, igst, rate_pct=18, direction="output")
    customer_id = _customer(client, company_id, "Inter State Co", state="Karnataka")

    invoice = client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "GST-INTER-1",
            "invoice_date": "2026-01-10",
            "due_date": "2026-02-09",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 10000,
            "gst_rate_id": rate["id"],
        },
    ).json()
    assert invoice["cgst_amount"] == 0.0
    assert invoice["sgst_amount"] == 0.0
    assert invoice["igst_amount"] == 1800.0
    assert invoice["amount"] == 11800.0

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Invoice GST-INTER-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {(ar_id, 11800.0, 0.0), (revenue_id, 0.0, 10000.0), (igst, 0.0, 1800.0)}


def test_vendor_bill_with_gst_and_tds_together(client, company):
    # GST (ITC on the purchase) and TDS (withheld from the vendor) are
    # unrelated deductions that both apply to the same bill -- GST affects
    # what's booked as expense-side tax, TDS affects what's actually paid.
    company_id = company["id"]
    _set_home_state(client, company_id, "Maharashtra")
    ap_id = _gl_account(client, company_id, "2320", "liability", forecast_role="accounts_payable")
    tds_payable_id = _gl_account(client, company_id, "2321", "liability", forecast_role="tds_payable")
    expense_id = _gl_account(client, company_id, "6900", "expense")
    cgst = _gl_account(client, company_id, "1320", "asset")
    sgst = _gl_account(client, company_id, "1321", "asset")
    igst = _gl_account(client, company_id, "1322", "asset")
    gst_rate = _gst_rate(client, company_id, cgst, sgst, igst, rate_pct=18, direction="input")

    tds_section = client.post(f"/tds-sections?company_id={company_id}", json={"section_code": "194J", "description": "Professional fees", "rate_pct": 10}).json()
    vendor_id = _vendor(client, company_id, "GST TDS Vendor", state="Maharashtra")

    bill = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={
            "vendor_id": vendor_id,
            "bill_number": "GST-TDS-1",
            "bill_date": "2026-01-05",
            "due_date": "2026-02-04",
            "expense_gl_account_id": expense_id,
            "net_amount": 10000,
            "gst_rate_id": gst_rate["id"],
            "tds_section_id": tds_section["id"],
        },
    ).json()
    assert bill["cgst_amount"] == 900.0
    assert bill["sgst_amount"] == 900.0
    assert bill["tds_amount"] == 1000.0  # TDS computed on net_amount, unaffected by GST
    # gross = 10000 + 900 + 900 = 11800; payable = 11800 - 1000 tds = 10800
    assert bill["amount"] == 10800.0

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Bill GST-TDS-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {
        (expense_id, 10000.0, 0.0),
        (cgst, 900.0, 0.0),
        (sgst, 900.0, 0.0),
        (tds_payable_id, 0.0, 1000.0),
        (ap_id, 0.0, 10800.0),
    }
    total_debit = sum(ln["debit_amount"] for ln in je["lines"])
    total_credit = sum(ln["credit_amount"] for ln in je["lines"])
    assert total_debit == total_credit == 11800.0


def test_gstr1_report_splits_b2b_b2c_and_hsn(client, company):
    company_id = company["id"]
    _set_home_state(client, company_id, "Maharashtra")
    _gl_account(client, company_id, "1302", "asset", forecast_role="accounts_receivable")
    revenue_id = _gl_account(client, company_id, "4802", "revenue", hsn_sac_code="998314")
    cgst = _gl_account(client, company_id, "2316", "liability")
    sgst = _gl_account(client, company_id, "2317", "liability")
    igst = _gl_account(client, company_id, "2318", "liability")
    rate = _gst_rate(client, company_id, cgst, sgst, igst, rate_pct=18, direction="output")

    b2b_customer = _customer(client, company_id, "Registered Buyer", state="Maharashtra", gstin="27AAAAA0000A1Z5")
    b2c_customer = _customer(client, company_id, "Walk-in Buyer", state="Maharashtra")

    for i, (cust, num) in enumerate([(b2b_customer, "B2B-1"), (b2c_customer, "B2C-1"), (b2c_customer, "B2C-2")]):
        client.post(
            f"/customer-invoices?company_id={company_id}",
            json={
                "customer_id": cust,
                "invoice_number": num,
                "invoice_date": "2026-01-10",
                "due_date": "2026-02-09",
                "revenue_gl_account_id": revenue_id,
                "net_amount": 10000,
                "gst_rate_id": rate["id"],
            },
        )

    report = client.get(f"/gstr1-report?company_id={company_id}&start=2026-01-01&end=2026-01-31").json()

    assert len(report["b2b_rows"]) == 1
    assert report["b2b_rows"][0]["customer_gstin"] == "27AAAAA0000A1Z5"
    assert report["b2b_rows"][0]["taxable_value"] == 10000.0

    assert len(report["b2c_rows"]) == 1
    assert report["b2c_rows"][0]["taxable_value"] == 20000.0  # two B2C invoices aggregated

    assert len(report["hsn_rows"]) == 1
    assert report["hsn_rows"][0]["hsn_sac_code"] == "998314"
    assert report["hsn_rows"][0]["taxable_value"] == 30000.0

    assert report["total_taxable_value"] == 30000.0
    assert report["total_tax"] == 5400.0  # 30000 * 18%


def test_gstr3b_report_nets_output_against_input(client, company):
    company_id = company["id"]
    _set_home_state(client, company_id, "Maharashtra")
    _gl_account(client, company_id, "1303", "asset", forecast_role="accounts_receivable")
    _gl_account(client, company_id, "2322", "liability", forecast_role="accounts_payable")
    revenue_id = _gl_account(client, company_id, "4803", "revenue")
    expense_id = _gl_account(client, company_id, "6901", "expense")
    out_cgst = _gl_account(client, company_id, "2330", "liability")
    out_sgst = _gl_account(client, company_id, "2331", "liability")
    out_igst = _gl_account(client, company_id, "2332", "liability")
    in_cgst = _gl_account(client, company_id, "1330", "asset")
    in_sgst = _gl_account(client, company_id, "1331", "asset")
    in_igst = _gl_account(client, company_id, "1332", "asset")
    output_rate = _gst_rate(client, company_id, out_cgst, out_sgst, out_igst, description="Output 18%", rate_pct=18, direction="output")
    input_rate = _gst_rate(client, company_id, in_cgst, in_sgst, in_igst, description="Input 18%", rate_pct=18, direction="input")

    customer_id = _customer(client, company_id, "3B Customer", state="Maharashtra")
    vendor_id = _vendor(client, company_id, "3B Vendor", state="Maharashtra")

    client.post(
        f"/customer-invoices?company_id={company_id}",
        json={
            "customer_id": customer_id,
            "invoice_number": "3B-INV-1",
            "invoice_date": "2026-01-10",
            "due_date": "2026-02-09",
            "revenue_gl_account_id": revenue_id,
            "net_amount": 10000,
            "gst_rate_id": output_rate["id"],
        },
    )
    client.post(
        f"/vendor-bills?company_id={company_id}",
        json={
            "vendor_id": vendor_id,
            "bill_number": "3B-BILL-1",
            "bill_date": "2026-01-15",
            "due_date": "2026-02-14",
            "expense_gl_account_id": expense_id,
            "net_amount": 4000,
            "gst_rate_id": input_rate["id"],
        },
    )

    report = client.get(f"/gstr3b-report?company_id={company_id}&start=2026-01-01&end=2026-01-31").json()
    assert report["output_cgst"] == 900.0
    assert report["output_sgst"] == 900.0
    assert report["input_cgst"] == 360.0
    assert report["input_sgst"] == 360.0
    assert report["net_cgst_payable"] == 540.0
    assert report["net_sgst_payable"] == 540.0
    assert report["net_tax_payable"] == 1080.0
