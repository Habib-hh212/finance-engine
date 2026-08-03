import io

import pandas as pd


def _xlsx_bytes(rows: list[dict]) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def test_upload_statements_xlsx_creates_accounts_and_actuals(client, company):
    company_id = company["id"]
    rows = [
        {"gl_account_code": "4000", "gl_account_name": "Product Sales", "category": "revenue", "period": "2023-01", "amount": 10000},
        {"gl_account_code": "4000", "gl_account_name": "Product Sales", "category": "revenue", "period": "2023-02", "amount": 11000},
        {"gl_account_code": "6000", "gl_account_name": "Rent", "category": "expense", "period": "2023-01", "amount": 2000},
    ]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows_imported"] == 3
    assert body["accounts_created"] == 2

    stmt = client.get(f"/reports/income-statement?company_id={company_id}&start_period=2023-01-01&end_period=2023-02-01").json()
    assert stmt["total_revenue"] == 21000
    assert stmt["total_expense"] == 2000


def test_upload_statements_reuses_existing_gl_account_by_code(client, company):
    company_id = company["id"]
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": "4100", "name": "Existing Sales", "category": "revenue"})
    existing_id = r.json()["id"]

    rows = [{"gl_account_code": "4100", "category": "revenue", "period": "2024-06", "amount": 500}]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["accounts_created"] == 0

    actuals = client.get(f"/actuals?company_id={company_id}&gl_account_id={existing_id}").json()
    assert any(a["amount"] == 500 for a in actuals)


def test_upload_statements_with_cost_center_tags_actual(client, company):
    company_id = company["id"]
    rows = [{"gl_account_code": "6200", "category": "expense", "period": "2024-01", "amount": 750, "cost_center_code": "CC-500"}]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["cost_centers_created"] == 1

    centers = client.get(f"/cost-centers?company_id={company_id}").json()
    assert any(c["code"] == "CC-500" for c in centers)


def test_upload_statements_rejects_invalid_category(client, company):
    company_id = company["id"]
    rows = [{"gl_account_code": "9999", "category": "not-a-category", "period": "2024-01", "amount": 1}]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 422


def test_upload_statements_rejects_category_mismatch_with_existing_account(client, company):
    company_id = company["id"]
    client.post(f"/gl-accounts?company_id={company_id}", json={"code": "4200", "name": "Sales", "category": "revenue"})
    rows = [{"gl_account_code": "4200", "category": "expense", "period": "2024-01", "amount": 1}]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 422


def test_upload_statements_rejects_missing_columns(client, company):
    company_id = company["id"]
    rows = [{"gl_account_code": "1000", "amount": 1}]  # missing category, period
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 422


def test_upload_statements_rejects_wrong_extension(client, company):
    company_id = company["id"]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.txt", b"not a spreadsheet", "text/plain")},
    )
    assert r.status_code == 400


def test_upload_statements_accepts_csv_too(client, company):
    company_id = company["id"]
    csv_content = b"gl_account_code,category,period,amount\n7000,revenue,2022-01,300\n"
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.csv", csv_content, "text/csv")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["rows_imported"] == 1


def test_upload_statements_can_cover_many_years(client, company):
    # This is the "store more than two years" case: a single upload spanning
    # four calendar years, all of which must be queryable afterward.
    company_id = company["id"]
    rows = [
        {"gl_account_code": "4300", "category": "revenue", "period": f"{year}-06", "amount": 1000 * (year - 2019)}
        for year in [2020, 2021, 2022, 2023]
    ]
    r = client.post(
        f"/reports/upload-statements?company_id={company_id}",
        files={"file": ("history.xlsx", _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["rows_imported"] == 4

    stmt = client.get(f"/reports/income-statement?company_id={company_id}&start_period=2020-01-01&end_period=2023-12-01").json()
    assert stmt["total_revenue"] == 1000 + 2000 + 3000 + 4000
