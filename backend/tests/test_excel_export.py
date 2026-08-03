XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _post_actual(client, company_id, gl_account_id, period, amount):
    r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_account_id, "period": period, "amount": amount})
    assert r.status_code == 200, r.text


def test_export_income_statement_returns_xlsx(client, company):
    company_id = company["id"]
    sales_id = _gl_account(client, company_id, "4600", "revenue")
    _post_actual(client, company_id, sales_id, "2026-01-01", 5000)

    r = client.get(f"/reports/income-statement/export?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-01")
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_MEDIA_TYPE
    assert "attachment" in r.headers["content-disposition"]
    assert len(r.content) > 0


def test_export_balance_sheet_returns_xlsx(client, company):
    company_id = company["id"]
    cash_id = _gl_account(client, company_id, "1300", "asset")
    _post_actual(client, company_id, cash_id, "2026-01-01", 100)

    r = client.get(f"/reports/balance-sheet/export?company_id={company_id}&as_of=2026-01-31")
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_MEDIA_TYPE


def test_export_statement_forecast_returns_xlsx(client, company):
    company_id = company["id"]
    r = client.get(f"/forecast/export?company_id={company_id}&start_period=2026-01-01&periods=2")
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_MEDIA_TYPE


def test_export_sales_forecast_returns_xlsx(client, company):
    company_id = company["id"]
    csv_content = b"sku,product_name,period,quantity,amount,currency\nW1,Widget,2026-01,5,5000,USD\nW1,Widget,2026-02,5,5000,USD\n"
    client.post(f"/sales/upload?company_id={company_id}", files={"file": ("s.csv", csv_content, "text/csv")})
    products = client.get(f"/products?company_id={company_id}").json()
    product_id = products[0]["id"]

    r = client.get(f"/sales/forecast/export?company_id={company_id}&product_id={product_id}&periods=2")
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_MEDIA_TYPE


def test_income_statement_trend_endpoint(client, company):
    company_id = company["id"]
    sales_id = _gl_account(client, company_id, "4700", "revenue")
    rent_id = _gl_account(client, company_id, "6700", "expense")
    _post_actual(client, company_id, sales_id, "2026-01-01", 1000)
    _post_actual(client, company_id, sales_id, "2026-02-01", 1500)
    _post_actual(client, company_id, rent_id, "2026-01-01", 200)

    r = client.get(f"/reports/income-statement/trend?company_id={company_id}&start_period=2026-01-01&end_period=2026-02-01")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    jan = next(row for row in rows if row["period"] == "2026-01-01")
    assert jan["revenue"] == 1000
    assert jan["expense"] == 200
    assert jan["net_profit"] == 800
