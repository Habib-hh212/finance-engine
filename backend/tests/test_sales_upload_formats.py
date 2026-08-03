import io

import pandas as pd


def test_sales_upload_accepts_xlsx(client, company):
    company_id = company["id"]
    rows = [
        {"sku": "X1", "product_name": "Gadget", "period": "2026-01", "quantity": 4, "amount": 4000, "currency": "USD"},
    ]
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, engine="openpyxl")

    r = client.post(
        f"/sales/upload?company_id={company_id}",
        files={"file": ("sales.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["rows_imported"] == 1


def test_sales_upload_rejects_unsupported_extension(client, company):
    company_id = company["id"]
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.txt", b"nope", "text/plain")})
    assert r.status_code == 400
