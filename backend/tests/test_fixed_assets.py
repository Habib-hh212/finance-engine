def _gl_account(client, company_id, code, category):
    r = client.post(f"/gl-accounts?company_id={company_id}", json={"code": code, "name": code, "category": category})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _standard_accounts(client, company_id, suffix=""):
    return {
        "cash": _gl_account(client, company_id, f"CASH{suffix}", "asset"),
        "apc": _gl_account(client, company_id, f"APC{suffix}", "asset"),
        "dep_expense": _gl_account(client, company_id, f"DEPEXP{suffix}", "expense"),
        "accum_dep": _gl_account(client, company_id, f"ACCUMDEP{suffix}", "asset"),
        "gain": _gl_account(client, company_id, f"GAIN{suffix}", "revenue"),
        "loss": _gl_account(client, company_id, f"LOSS{suffix}", "expense"),
    }


def _asset_class(client, company_id, accounts, method="straight_line", life=5, factor=2.0, suffix=""):
    r = client.post(
        f"/asset-classes?company_id={company_id}",
        json={
            "name": f"Equipment{suffix}",
            "apc_gl_account_id": accounts["apc"],
            "depreciation_expense_gl_account_id": accounts["dep_expense"],
            "accumulated_depreciation_gl_account_id": accounts["accum_dep"],
            "disposal_gain_gl_account_id": accounts["gain"],
            "disposal_loss_gl_account_id": accounts["loss"],
            "default_depreciation_method": method,
            "default_useful_life_years": life,
            "default_declining_balance_factor": factor,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _acquire(client, company_id, asset_class_id, accounts, cost, salvage=0, life=None, method=None, factor=None, code="A-1", acq_date="2026-01-01"):
    payload = {
        "asset_class_id": asset_class_id,
        "code": code,
        "name": code,
        "acquisition_date": acq_date,
        "capitalized_cost": cost,
        "funding_gl_account_id": accounts["cash"],
        "salvage_value": salvage,
    }
    if life is not None:
        payload["useful_life_years"] = life
    if method is not None:
        payload["depreciation_method"] = method
    if factor is not None:
        payload["declining_balance_factor"] = factor
    r = client.post(f"/assets?company_id={company_id}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# --- Acquisition -----------------------------------------------------


def test_acquiring_an_asset_posts_a_balanced_journal_entry(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "1")
    asset_class = _asset_class(client, company_id, accounts, suffix="1")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=12000, life=5, code="A-101")

    assert asset["status"] == "active"
    assert asset["capitalized_cost"] == 12000
    assert asset["accumulated_depreciation"] == 0
    assert asset["net_book_value"] == 12000

    journal_entries = client.get(f"/journal-entries?company_id={company_id}").json()
    acquisition = next(e for e in journal_entries if e["reference"] == "Asset acquisition: A-101")
    assert acquisition["status"] == "posted"
    assert {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in acquisition["lines"]} == {
        (accounts["apc"], 12000.0, 0.0),
        (accounts["cash"], 0.0, 12000.0),
    }


def test_asset_class_rejects_gl_account_from_another_company(client, company):
    company_id = company["id"]
    other = client.post("/companies", json={"name": "Other Co", "base_currency": "USD"}).json()
    other_gl = _gl_account(client, other["id"], "OTHERGL", "asset")
    accounts = _standard_accounts(client, company_id, "2")

    r = client.post(
        f"/asset-classes?company_id={company_id}",
        json={
            "name": "Bad Class",
            "apc_gl_account_id": other_gl,
            "depreciation_expense_gl_account_id": accounts["dep_expense"],
            "accumulated_depreciation_gl_account_id": accounts["accum_dep"],
            "disposal_gain_gl_account_id": accounts["gain"],
            "disposal_loss_gl_account_id": accounts["loss"],
        },
    )
    assert r.status_code == 422


# --- Depreciation methods ---------------------------------------------


def test_straight_line_depreciation(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "SL")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="SL")
    # 12000 cost, 0 salvage, 5 years -> 60 months -> 200.00/month exactly
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=12000, salvage=0, life=5, code="SL-1")

    r = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")
    assert r.status_code == 200, r.text
    body = r.json()
    row = next(row for row in body["rows"] if row["asset_id"] == asset["id"])
    assert row["depreciation_amount"] == 200.0

    r2 = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-02-01")
    row2 = next(row for row in r2.json()["rows"] if row["asset_id"] == asset["id"])
    assert row2["depreciation_amount"] == 200.0

    updated = client.get(f"/assets/{asset['id']}?company_id={company_id}").json()
    assert updated["accumulated_depreciation"] == 400.0
    assert updated["net_book_value"] == 11600.0


def test_declining_balance_depreciation(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "DB")
    asset_class = _asset_class(client, company_id, accounts, method="declining_balance", life=4, factor=2.0, suffix="DB")
    # 2400 cost, 0 salvage, 4 years, factor 2 -> monthly rate = (2/4)/12 = 1/24
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=2400, salvage=0, life=4, method="declining_balance", factor=2.0, code="DB-1")

    r1 = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")
    row1 = next(row for row in r1.json()["rows"] if row["asset_id"] == asset["id"])
    assert row1["depreciation_amount"] == 100.0  # 2400 / 24

    r2 = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-02-01")
    row2 = next(row for row in r2.json()["rows"] if row["asset_id"] == asset["id"])
    assert row2["depreciation_amount"] == 95.83  # (2400-100) / 24, rounded

    updated = client.get(f"/assets/{asset['id']}?company_id={company_id}").json()
    assert updated["accumulated_depreciation"] == 195.83


def test_sum_of_years_digits_depreciation(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "SYD")
    asset_class = _asset_class(client, company_id, accounts, method="sum_of_years_digits", life=2, suffix="SYD")
    # 3000 cost, 0 salvage, 2 years -> 24 months, syd_sum = 24*25/2 = 300
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=3000, salvage=0, life=2, method="sum_of_years_digits", code="SYD-1")

    r1 = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")
    row1 = next(row for row in r1.json()["rows"] if row["asset_id"] == asset["id"])
    assert row1["depreciation_amount"] == 240.0  # 3000 * 24/300

    r2 = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-02-01")
    row2 = next(row for row in r2.json()["rows"] if row["asset_id"] == asset["id"])
    assert row2["depreciation_amount"] == 230.0  # 3000 * 23/300


def test_depreciation_never_goes_below_salvage_value(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "FLOOR")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=1, suffix="FLOOR")
    # 1200 cost, 1000 salvage, 1 year -> depreciable base 200, 12 months -> 16.6667/month
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=1200, salvage=1000, life=1, code="FLOOR-1")

    total = 0.0
    for month in range(1, 15):  # run well past the 12-month life
        period = f"2026-{month:02d}-01" if month <= 12 else f"2027-{month - 12:02d}-01"
        r = client.post(f"/assets/depreciation-run?company_id={company_id}&period={period}")
        row = next(row for row in r.json()["rows"] if row["asset_id"] == asset["id"])
        total += row["depreciation_amount"]

    updated = client.get(f"/assets/{asset['id']}?company_id={company_id}").json()
    assert updated["accumulated_depreciation"] == 200.0  # never exceeds depreciable base
    assert updated["net_book_value"] == 1000.0  # never drops below salvage


def test_depreciation_run_is_idempotent_per_period(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "IDEM")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="IDEM")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="IDEM-1")

    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")
    r2 = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")
    row2 = next(row for row in r2.json()["rows"] if row["asset_id"] == asset["id"])
    assert row2["depreciation_amount"] == 0.0
    assert row2["skipped_reason"] is not None

    updated = client.get(f"/assets/{asset['id']}?company_id={company_id}").json()
    assert updated["accumulated_depreciation"] == 100.0  # only counted once (6000/60)


def test_depreciation_run_posts_a_balanced_journal_entry(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "JE")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="JE")
    _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="JE-1")
    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    dep_entry = next(e for e in entries if e["reference"] == "Depreciation: JE-1")
    assert dep_entry["status"] == "posted"
    assert {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in dep_entry["lines"]} == {
        (accounts["dep_expense"], 100.0, 0.0),
        (accounts["accum_dep"], 0.0, 100.0),
    }


# --- Transfer -----------------------------------------------------------


def test_transfer_reassigns_cost_center_without_gl_postings(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "XFER")
    asset_class = _asset_class(client, company_id, accounts, suffix="XFER")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=1000, life=5, code="XFER-1")

    cc = client.post(f"/cost-centers?company_id={company_id}", json={"code": "CC1", "name": "Ops"}).json()
    before_count = len(client.get(f"/journal-entries?company_id={company_id}").json())

    r = client.post(f"/assets/{asset['id']}/transfer?company_id={company_id}", json={"to_cost_center_id": cc["id"], "reason": "Moved to Ops"})
    assert r.status_code == 200, r.text
    assert r.json()["cost_center_id"] == cc["id"]

    after_count = len(client.get(f"/journal-entries?company_id={company_id}").json())
    assert after_count == before_count  # no GL impact


# --- Disposal -----------------------------------------------------------


def test_dispose_by_sale_with_a_gain(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "GAIN")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="GAIN")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="GAIN-1")
    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")  # accumulated = 100, NBV = 5900

    r = client.post(
        f"/assets/{asset['id']}/dispose?company_id={company_id}",
        json={"disposal_type": "sale", "disposal_date": "2026-02-01", "proceeds": 6200, "proceeds_gl_account_id": accounts["cash"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["gain_or_loss"] == 300.0  # 6200 - 5900
    assert body["asset"]["status"] == "sold"

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    disposal = next(e for e in entries if e["reference"] == "Disposal (sale): GAIN-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in disposal["lines"]}
    assert lines == {
        (accounts["accum_dep"], 100.0, 0.0),
        (accounts["apc"], 0.0, 6000.0),
        (accounts["cash"], 6200.0, 0.0),
        (accounts["gain"], 0.0, 300.0),
    }


def test_dispose_by_sale_with_a_loss(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "LOSS")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="LOSS")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="LOSS-1")
    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")  # NBV = 5900

    r = client.post(
        f"/assets/{asset['id']}/dispose?company_id={company_id}",
        json={"disposal_type": "sale", "disposal_date": "2026-02-01", "proceeds": 5000, "proceeds_gl_account_id": accounts["cash"]},
    )
    body = r.json()
    assert body["gain_or_loss"] == -900.0  # 5000 - 5900


def test_scrap_with_zero_proceeds_writes_off_remaining_nbv_as_a_loss(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "SCRAP")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="SCRAP")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="SCRAP-1")
    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")  # accumulated=100, NBV=5900

    r = client.post(
        f"/assets/{asset['id']}/dispose?company_id={company_id}",
        json={"disposal_type": "scrap", "disposal_date": "2026-02-01", "reason": "Beyond repair"},
    )
    body = r.json()
    assert body["gain_or_loss"] == -5900.0
    assert body["asset"]["status"] == "scrapped"

    entries = client.get(f"/journal-entries?company_id={company_id}").json()
    disposal = next(e for e in entries if e["reference"] == "Disposal (scrap): SCRAP-1")
    lines = {(ln["gl_account_id"], ln["debit_amount"], ln["credit_amount"]) for ln in disposal["lines"]}
    assert lines == {
        (accounts["accum_dep"], 100.0, 0.0),
        (accounts["apc"], 0.0, 6000.0),
        (accounts["loss"], 5900.0, 0.0),
    }


def test_lost_asset_is_written_off_with_a_reason(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "LOST")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="LOST")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=3000, life=5, code="LOST-1")

    r = client.post(
        f"/assets/{asset['id']}/dispose?company_id={company_id}",
        json={"disposal_type": "lost", "disposal_date": "2026-01-15", "reason": "Stolen from warehouse"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["asset"]["status"] == "lost"
    assert body["asset"]["disposal_reason"] == "Stolen from warehouse"
    assert body["gain_or_loss"] == -3000.0  # full cost written off, nothing depreciated yet


def test_disposed_asset_is_excluded_from_future_depreciation_runs(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "STOP")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="STOP")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="STOP-1")
    client.post(f"/assets/{asset['id']}/dispose?company_id={company_id}", json={"disposal_type": "scrap", "disposal_date": "2026-01-15"})

    r = client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-02-01")
    assert not any(row["asset_id"] == asset["id"] for row in r.json()["rows"])


def test_disposed_asset_cannot_be_disposed_again(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "TWICE")
    asset_class = _asset_class(client, company_id, accounts, suffix="TWICE")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=1000, life=5, code="TWICE-1")
    client.post(f"/assets/{asset['id']}/dispose?company_id={company_id}", json={"disposal_type": "scrap", "disposal_date": "2026-01-15"})

    r = client.post(f"/assets/{asset['id']}/dispose?company_id={company_id}", json={"disposal_type": "scrap", "disposal_date": "2026-01-16"})
    assert r.status_code == 409


# --- Asset register -------------------------------------------------------


def test_asset_register_totals(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "REG")
    asset_class = _asset_class(client, company_id, accounts, method="straight_line", life=5, suffix="REG")
    _acquire(client, company_id, asset_class["id"], accounts, cost=6000, life=5, code="REG-1")
    _acquire(client, company_id, asset_class["id"], accounts, cost=3000, life=5, code="REG-2")
    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")

    r = client.get(f"/assets/register?company_id={company_id}&as_of=2026-01-31")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["rows"]) == 2
    assert body["total_capitalized_cost"] == 9000.0
    assert body["total_accumulated_depreciation"] == 150.0  # 100 + 50
    assert body["total_net_book_value"] == 8850.0


def test_fixed_asset_mutations_are_audited(client, company):
    company_id = company["id"]
    accounts = _standard_accounts(client, company_id, "AUDIT")
    asset_class = _asset_class(client, company_id, accounts, suffix="AUDIT")
    asset = _acquire(client, company_id, asset_class["id"], accounts, cost=1000, life=5, code="AUDIT-1")
    client.post(f"/assets/depreciation-run?company_id={company_id}&period=2026-01-01")
    client.post(f"/assets/{asset['id']}/dispose?company_id={company_id}", json={"disposal_type": "scrap", "disposal_date": "2026-02-01"})

    entries = client.get(f"/audit-log?company_id={company_id}&entity_type=asset").json()
    actions = [e["action"] for e in entries]
    assert "create" in actions
    assert "depreciation_run" in actions
    assert "dispose" in actions
