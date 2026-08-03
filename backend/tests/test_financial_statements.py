def _gl_account(client, company_id, code, name, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": name, "category": category})
    assert r.status_code == 200, r.text
    return r.json()


def _post_actual(client, company_id, gl_account_id, period, amount):
    r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_account_id, "period": period, "amount": amount})
    assert r.status_code == 200, r.text
    return r.json()


def _line_for(lines, gl_account_id):
    matches = [line for line in lines if line["gl_account_id"] == gl_account_id]
    assert len(matches) == 1
    return matches[0]


def test_income_statement_revenue_minus_expense(client, company):
    company_id = company["id"]
    sales_acc = _gl_account(client, company_id, "4000", "Product Sales", "revenue")
    rent_acc = _gl_account(client, company_id, "6000", "Rent", "expense")

    _post_actual(client, company_id, sales_acc["id"], "2026-01-01", 50000)
    _post_actual(client, company_id, sales_acc["id"], "2026-02-01", 60000)
    _post_actual(client, company_id, rent_acc["id"], "2026-01-01", 5000)
    _post_actual(client, company_id, rent_acc["id"], "2026-02-01", 5000)

    r = client.get(f"/reports/income-statement?company_id={company_id}&start_period=2026-01-01&end_period=2026-02-01")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["total_revenue"] == 110000
    assert body["total_expense"] == 10000
    assert body["net_profit"] == 100000
    assert _line_for(body["revenue_lines"], sales_acc["id"])["amount"] == 110000
    assert _line_for(body["expense_lines"], rent_acc["id"])["amount"] == 10000


def test_income_statement_excludes_periods_outside_range(client, company):
    company_id = company["id"]
    sales_acc = _gl_account(client, company_id, "4001", "Sales", "revenue")
    _post_actual(client, company_id, sales_acc["id"], "2025-12-01", 99999)  # before range
    _post_actual(client, company_id, sales_acc["id"], "2026-01-01", 1000)
    _post_actual(client, company_id, sales_acc["id"], "2026-04-01", 88888)  # after range

    r = client.get(f"/reports/income-statement?company_id={company_id}&start_period=2026-01-01&end_period=2026-02-01")
    body = r.json()
    assert body["total_revenue"] == 1000


def test_income_statement_ignores_balance_sheet_accounts(client, company):
    company_id = company["id"]
    cash_acc = _gl_account(client, company_id, "1000", "Cash", "asset")
    _post_actual(client, company_id, cash_acc["id"], "2026-01-01", 5000)

    r = client.get(f"/reports/income-statement?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-01")
    body = r.json()
    assert body["total_revenue"] == 0
    assert body["total_expense"] == 0
    assert body["revenue_lines"] == []
    assert body["expense_lines"] == []


def test_balance_sheet_balances_when_consistent(client, company):
    company_id = company["id"]
    cash_acc = _gl_account(client, company_id, "1000", "Cash", "asset")
    loan_acc = _gl_account(client, company_id, "2000", "Bank Loan", "liability")
    equity_acc = _gl_account(client, company_id, "3000", "Owner Equity", "equity")

    _post_actual(client, company_id, cash_acc["id"], "2026-01-01", 10000)
    _post_actual(client, company_id, loan_acc["id"], "2026-01-01", 4000)
    _post_actual(client, company_id, equity_acc["id"], "2026-01-01", 6000)

    r = client.get(f"/reports/balance-sheet?company_id={company_id}&as_of=2026-01-31")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["total_assets"] == 10000
    assert body["total_liabilities"] == 4000
    assert body["total_equity"] == 6000
    assert body["is_balanced"] is True
    assert body["difference"] == 0


def test_balance_sheet_flags_when_not_balanced(client, company):
    company_id = company["id"]
    cash_acc = _gl_account(client, company_id, "1001", "Petty Cash", "asset")
    _post_actual(client, company_id, cash_acc["id"], "2026-01-01", 500)
    # no offsetting liability/equity posted

    r = client.get(f"/reports/balance-sheet?company_id={company_id}&as_of=2026-01-31")
    body = r.json()
    assert body["total_assets"] == 500
    assert body["total_liabilities"] == 0
    assert body["total_equity"] == 0
    assert body["is_balanced"] is False
    assert body["difference"] == 500


def test_balance_sheet_is_cumulative_as_of_date(client, company):
    company_id = company["id"]
    cash_acc = _gl_account(client, company_id, "1002", "Operating Cash", "asset")
    _post_actual(client, company_id, cash_acc["id"], "2026-01-01", 1000)
    _post_actual(client, company_id, cash_acc["id"], "2026-02-01", 500)
    _post_actual(client, company_id, cash_acc["id"], "2026-06-01", 999999)  # after the as-of date

    r = client.get(f"/reports/balance-sheet?company_id={company_id}&as_of=2026-03-01")
    body = r.json()
    assert body["total_assets"] == 1500


def test_balance_sheet_ignores_income_statement_accounts(client, company):
    company_id = company["id"]
    sales_acc = _gl_account(client, company_id, "4002", "Sales", "revenue")
    _post_actual(client, company_id, sales_acc["id"], "2026-01-01", 7777)

    r = client.get(f"/reports/balance-sheet?company_id={company_id}&as_of=2026-01-31")
    body = r.json()
    assert body["total_assets"] == 0
    assert body["asset_lines"] == []
