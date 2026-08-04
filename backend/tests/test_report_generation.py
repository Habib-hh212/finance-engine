PDF_MEDIA_TYPE = "application/pdf"
PPTX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _post_actual(client, company_id, gl_account_id, period, amount):
    r = client.post(f"/actuals?company_id={company_id}", json={"gl_account_id": gl_account_id, "period": period, "amount": amount})
    assert r.status_code == 200, r.text


def test_board_report_pdf_returns_a_real_pdf(client, company):
    company_id = company["id"]
    sales_id = _gl_account(client, company_id, "4800", "revenue")
    _post_actual(client, company_id, sales_id, "2026-01-01", 5000)

    r = client.get(f"/reports/board-report/pdf?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-01&as_of=2026-01-31")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == PDF_MEDIA_TYPE
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")


def test_board_report_pptx_returns_a_real_pptx(client, company):
    company_id = company["id"]
    sales_id = _gl_account(client, company_id, "4801", "revenue")
    _post_actual(client, company_id, sales_id, "2026-01-01", 7000)

    r = client.get(f"/reports/board-report/pptx?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-01&as_of=2026-01-31")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == PPTX_MEDIA_TYPE
    assert r.content[:2] == b"PK"  # pptx is a zip container


def test_board_report_works_with_no_data(client, company):
    company_id = company["id"]
    r = client.get(f"/reports/board-report/pdf?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-01&as_of=2026-01-31")
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF")


def test_board_report_filename_is_sanitized(client):
    r = client.post("/companies", json={"name": 'Weird / Co: "Name"?', "base_currency": "USD"})
    company_id = r.json()["id"]
    r = client.get(f"/reports/board-report/pdf?company_id={company_id}&start_period=2026-01-01&end_period=2026-01-01&as_of=2026-01-31")
    assert r.status_code == 200, r.text
    filename = r.headers["content-disposition"].split("filename=")[1].strip('"')
    assert all(c not in filename for c in ['"', "/", ":", "?"])
