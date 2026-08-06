from app.services import payroll_tax

# --- payroll_tax pure calculations ------------------------------------------


def test_new_regime_rebate_below_12_lakh():
    assert payroll_tax.compute_annual_tax(1_000_000, "new") == 0.0


def test_new_regime_above_rebate_ceiling():
    assert payroll_tax.compute_annual_tax(1_500_000, "new") == 109_200.0


def test_old_regime_rebate_below_5_lakh():
    assert payroll_tax.compute_annual_tax(400_000, "old") == 0.0


def test_old_regime_above_rebate_ceiling():
    assert payroll_tax.compute_annual_tax(600_000, "old") == 33_800.0


def test_hra_exemption_metro():
    exemption = payroll_tax.hra_exemption(basic_annual=600_000, hra_received_annual=300_000, rent_paid_annual=360_000, is_metro=True)
    assert exemption == 300_000.0


def test_hra_exemption_no_rent_paid():
    assert payroll_tax.hra_exemption(basic_annual=600_000, hra_received_annual=300_000, rent_paid_annual=0, is_metro=True) == 0.0


def test_new_regime_ignores_investment_declarations():
    breakdown = payroll_tax.estimate_annual_tds(
        basic_monthly=150_000,
        hra_monthly=60_000,
        special_allowance_monthly=30_000,
        other_allowance_monthly=0,
        regime="new",
        section_80c=150_000,
        rent_paid_monthly=50_000,
    )
    assert breakdown.hra_exemption_amount == 0.0
    assert breakdown.chapter_via_deductions == 0.0
    assert breakdown.standard_deduction == 75_000.0


def test_old_regime_applies_declarations():
    breakdown = payroll_tax.estimate_annual_tds(
        basic_monthly=50_000,
        hra_monthly=20_000,
        special_allowance_monthly=0,
        other_allowance_monthly=0,
        regime="old",
        is_metro=True,
        section_80c=150_000,
        rent_paid_monthly=30_000,
    )
    assert breakdown.standard_deduction == 50_000.0
    assert breakdown.chapter_via_deductions == 150_000.0
    assert breakdown.hra_exemption_amount > 0


# --- API integration ---------------------------------------------------------


def _gl_account(client, company_id, code, category, forecast_role=None):
    payload = {"code": code, "name": code, "category": category}
    if forecast_role:
        payload["forecast_role"] = forecast_role
    r = client.post(f"/gl-accounts?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _setup_payroll_accounts(client, company_id, suffix):
    return {
        "salary": _gl_account(client, company_id, f"7{suffix}", "expense", forecast_role="salary_expense"),
        "pf": _gl_account(client, company_id, f"21{suffix}", "liability", forecast_role="pf_payable"),
        "esi": _gl_account(client, company_id, f"22{suffix}", "liability", forecast_role="esi_payable"),
        "pt": _gl_account(client, company_id, f"23{suffix}", "liability", forecast_role="professional_tax_payable"),
        "tds": _gl_account(client, company_id, f"24{suffix}", "liability", forecast_role="tds_payable"),
        "cash": _gl_account(client, company_id, f"10{suffix}", "asset", forecast_role="cash"),
    }


def _employee(client, company_id, **overrides):
    payload = {
        "name": "Jane Employee",
        "date_of_joining": "2024-01-01",
        "tax_regime": "new",
        "basic_monthly": 50_000,
        "hra_monthly": 20_000,
        "special_allowance_monthly": 10_000,
        "other_allowance_monthly": 0,
    }
    payload.update(overrides)
    r = client.post(f"/employees?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_employee_crud(client, company):
    company_id = company["id"]
    employee = _employee(client, company_id, name="Alice")
    assert employee["is_active"] is True

    r = client.patch(f"/employees/{employee['id']}?company_id={company_id}", json={"basic_monthly": 55_000})
    assert r.status_code == 200
    assert r.json()["basic_monthly"] == 55_000.0

    listed = client.get(f"/employees?company_id={company_id}").json()
    assert any(e["id"] == employee["id"] for e in listed)


def test_payroll_run_high_earner_and_low_earner(client, company):
    company_id = company["id"]
    accounts = _setup_payroll_accounts(client, company_id, "1")

    high = _employee(
        client,
        company_id,
        name="High Earner",
        basic_monthly=150_000,
        hra_monthly=60_000,
        special_allowance_monthly=30_000,
    )
    low = _employee(
        client,
        company_id,
        name="Low Earner",
        basic_monthly=15_000,
        hra_monthly=5_000,
        special_allowance_monthly=0,
    )

    r = client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 6, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-06-30"},
    )
    assert r.status_code == 200, r.text
    run = r.json()
    assert len(run["payslips"]) == 2

    by_employee = {p["employee_id"]: p for p in run["payslips"]}
    high_slip = by_employee[high["id"]]
    low_slip = by_employee[low["id"]]

    assert high_slip["gross_pay"] == 240_000.0
    assert high_slip["pf_employee"] == 18_000.0
    assert high_slip["esi_employee"] == 0.0  # above ESI wage ceiling
    assert high_slip["professional_tax"] == 200.0
    assert high_slip["tds_amount"] == 36_530.0
    assert high_slip["net_pay"] == 185_270.0

    assert low_slip["gross_pay"] == 20_000.0
    assert low_slip["pf_employee"] == 1_800.0
    assert low_slip["esi_employee"] == 150.0  # under ESI wage ceiling
    assert low_slip["tds_amount"] == 0.0
    assert low_slip["net_pay"] == 17_850.0

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    je = next(e for e in entries if e["reference"] == "Payroll 6/2026")
    total_debit = round(sum(ln["debit_amount"] for ln in je["lines"]), 2)
    total_credit = round(sum(ln["credit_amount"] for ln in je["lines"]), 2)
    assert total_debit == total_credit

    cash_line = next(ln for ln in je["lines"] if ln["gl_account_id"] == accounts["cash"])
    assert cash_line["credit_amount"] == round(high_slip["net_pay"] + low_slip["net_pay"], 2)


def test_payroll_run_duplicate_period_errors(client, company):
    company_id = company["id"]
    accounts = _setup_payroll_accounts(client, company_id, "2")
    _employee(client, company_id)

    payload = {"period_month": 7, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-07-31"}
    r1 = client.post("/payroll-runs", params={"company_id": company_id}, json=payload)
    assert r1.status_code == 200, r1.text

    r2 = client.post("/payroll-runs", params={"company_id": company_id}, json=payload)
    assert r2.status_code == 422
    assert "already been run" in r2.json()["detail"]


def test_payroll_run_missing_gl_role_errors(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1099", "asset", forecast_role="cash")
    _employee(client, company_id)

    r = client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 8, "period_year": 2026, "cash_gl_account_id": cash_id, "run_date": "2026-08-31"},
    )
    assert r.status_code == 422
    assert "Salary Expense" in r.json()["detail"]


def test_old_regime_investment_declaration_reduces_tds(client, company):
    company_id = company["id"]
    accounts = _setup_payroll_accounts(client, company_id, "3")
    employee = _employee(
        client,
        company_id,
        name="Old Regime Employee",
        tax_regime="old",
        basic_monthly=150_000,
        hra_monthly=60_000,
        special_allowance_monthly=30_000,
        is_metro=True,
    )

    run_without = client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 4, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-04-30"},
    ).json()
    tds_without = run_without["payslips"][0]["tds_amount"]

    decl = client.post(
        f"/employees/{employee['id']}/investment-declarations?company_id={company_id}",
        json={"financial_year": 2026, "section_80c": 150_000, "section_80d": 25_000, "rent_paid_monthly": 40_000},
    )
    assert decl.status_code == 200, decl.text

    run_with = client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 5, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-05-31"},
    ).json()
    tds_with = run_with["payslips"][0]["tds_amount"]

    assert tds_with < tds_without


def test_form16_aggregates_multiple_runs(client, company):
    company_id = company["id"]
    accounts = _setup_payroll_accounts(client, company_id, "4")
    employee = _employee(client, company_id, name="Form16 Employee", basic_monthly=20_000, hra_monthly=8_000, special_allowance_monthly=0)

    client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 4, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-04-30"},
    )
    client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 5, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-05-31"},
    )

    r = client.get(f"/employees/{employee['id']}/form16", params={"company_id": company_id, "financial_year": 2026})
    assert r.status_code == 200, r.text
    summary = r.json()
    assert len(summary["months"]) == 2
    assert summary["total_gross"] == round(28_000.0 * 2, 2)

    pdf = client.get(f"/employees/{employee['id']}/form16/pdf", params={"company_id": company_id, "financial_year": 2026})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


def test_payslip_pdf_download(client, company):
    company_id = company["id"]
    accounts = _setup_payroll_accounts(client, company_id, "5")
    _employee(client, company_id)

    run = client.post(
        "/payroll-runs",
        params={"company_id": company_id},
        json={"period_month": 9, "period_year": 2026, "cash_gl_account_id": accounts["cash"], "run_date": "2026-09-30"},
    ).json()

    payslip_id = run["payslips"][0]["id"]
    pdf = client.get(f"/payslips/{payslip_id}/pdf", params={"company_id": company_id})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
