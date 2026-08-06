def _gl_account(client, company_id, code, category, forecast_role=None):
    payload = {"code": code, "name": code, "category": category}
    if forecast_role:
        payload["forecast_role"] = forecast_role
    r = client.post(f"/gl-accounts?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _vendor(client, company_id, name="TDS Vendor"):
    r = client.post(f"/vendors?company_id={company_id}", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _tds_section(client, company_id, section_code="194J", description="Professional fees", rate_pct=10):
    r = client.post(f"/tds-sections?company_id={company_id}", json={"section_code": section_code, "description": description, "rate_pct": rate_pct})
    assert r.status_code == 200, r.text
    return r.json()


def test_tds_section_create_list_update(client, company):
    company_id = company["id"]
    section = _tds_section(client, company_id)
    assert section["section_code"] == "194J"
    assert section["rate_pct"] == 10.0
    assert section["is_active"] is True

    listed = client.get(f"/tds-sections?company_id={company_id}").json()
    assert any(s["id"] == section["id"] for s in listed)

    r = client.patch(f"/tds-sections/{section['id']}?company_id={company_id}", json={"rate_pct": 2, "is_active": False})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["rate_pct"] == 2.0
    assert updated["is_active"] is False


def test_vendor_bill_without_tds_section_is_unaffected(client, company):
    company_id = company["id"]
    ap_id = _gl_account(client, company_id, "2200", "liability", forecast_role="accounts_payable")
    expense_id = _gl_account(client, company_id, "6800", "expense")
    vendor_id = _vendor(client, company_id, "Plain Vendor")

    bill = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={"vendor_id": vendor_id, "bill_number": "TDS-PLAIN-1", "bill_date": "2026-01-05", "due_date": "2026-02-04", "expense_gl_account_id": expense_id, "net_amount": 1000},
    ).json()
    assert bill["amount"] == 1000.0
    assert bill["tds_amount"] == 0.0
    assert bill["tds_section_id"] is None

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Bill TDS-PLAIN-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {(expense_id, 1000.0, 0.0), (ap_id, 0.0, 1000.0)}


def test_vendor_bill_with_tds_section_deducts_and_posts_three_lines(client, company):
    company_id = company["id"]
    ap_id = _gl_account(client, company_id, "2201", "liability", forecast_role="accounts_payable")
    tds_payable_id = _gl_account(client, company_id, "2202", "liability", forecast_role="tds_payable")
    expense_id = _gl_account(client, company_id, "6801", "expense")
    vendor_id = _vendor(client, company_id, "Professional Vendor")
    section = _tds_section(client, company_id, "194J", "Professional fees", 10)

    bill = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={
            "vendor_id": vendor_id,
            "bill_number": "TDS-1",
            "bill_date": "2026-01-05",
            "due_date": "2026-02-04",
            "expense_gl_account_id": expense_id,
            "net_amount": 10000,
            "tds_section_id": section["id"],
        },
    ).json()
    assert bill["tds_section_id"] == section["id"]
    assert bill["tds_amount"] == 1000.0
    assert bill["amount"] == 9000.0  # payable to vendor, net of TDS

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Bill TDS-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in je["lines"]}
    assert lines == {(expense_id, 10000.0, 0.0), (tds_payable_id, 0.0, 1000.0), (ap_id, 0.0, 9000.0)}
    total_debit = sum(ln["debit_amount"] for ln in je["lines"])
    total_credit = sum(ln["credit_amount"] for ln in je["lines"])
    assert total_debit == total_credit == 10000.0


def test_vendor_bill_with_tds_but_no_tds_payable_account_errors(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "2203", "liability", forecast_role="accounts_payable")
    expense_id = _gl_account(client, company_id, "6802", "expense")
    vendor_id = _vendor(client, company_id, "No TDS Account Vendor")
    section = _tds_section(client, company_id, "194C", "Contractor payments", 2)

    r = client.post(
        f"/vendor-bills?company_id={company_id}",
        json={
            "vendor_id": vendor_id,
            "bill_number": "TDS-2",
            "bill_date": "2026-01-05",
            "due_date": "2026-02-04",
            "expense_gl_account_id": expense_id,
            "net_amount": 5000,
            "tds_section_id": section["id"],
        },
    )
    assert r.status_code == 422
    assert "TDS Payable" in r.json()["detail"]


def test_tds_report_aggregates_by_section_and_vendor(client, company):
    company_id = company["id"]
    _gl_account(client, company_id, "2204", "liability", forecast_role="accounts_payable")
    _gl_account(client, company_id, "2205", "liability", forecast_role="tds_payable")
    expense_id = _gl_account(client, company_id, "6803", "expense")
    vendor_a = _vendor(client, company_id, "Report Vendor A")
    vendor_b = _vendor(client, company_id, "Report Vendor B")
    section = _tds_section(client, company_id, "194J", "Professional fees", 10)

    for i, (vendor_id, amount) in enumerate([(vendor_a, 10000), (vendor_a, 5000), (vendor_b, 2000)]):
        client.post(
            f"/vendor-bills?company_id={company_id}",
            json={
                "vendor_id": vendor_id,
                "bill_number": f"TDS-RPT-{i}",
                "bill_date": "2026-01-10",
                "due_date": "2026-02-09",
                "expense_gl_account_id": expense_id,
                "net_amount": amount,
                "tds_section_id": section["id"],
            },
        )

    report = client.get(f"/tds-report?company_id={company_id}&start=2026-01-01&end=2026-01-31").json()
    assert report["total_tds"] == 1700.0  # (10000+5000+2000) * 10%

    assert len(report["section_rows"]) == 1
    section_row = report["section_rows"][0]
    assert section_row["section_code"] == "194J"
    assert section_row["tds_amount"] == 1700.0

    deductee_by_name = {r["vendor_name"]: r for r in report["deductee_rows"]}
    assert deductee_by_name["Report Vendor A"]["tds_amount"] == 1500.0
    assert deductee_by_name["Report Vendor B"]["tds_amount"] == 200.0
