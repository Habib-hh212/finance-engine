from datetime import date

import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta

from app.services import forecasting, ml_forecasting


def _monthly_series(values: list[float], start=date(2026, 1, 1)) -> pd.Series:
    index = [start + relativedelta(months=i) for i in range(len(values))]
    return pd.Series(values, index=index)


FLAT_8 = _monthly_series([100.0] * 8)
SHORT_5 = _monthly_series([100.0] * 5)
VARIED_10 = _monthly_series([100.0, 105.0, 98.0, 110.0, 102.0, 108.0, 99.0, 111.0, 104.0, 107.0])


def test_random_forest_requires_min_history():
    with pytest.raises(ValueError, match="at least 6 months"):
        ml_forecasting.random_forest(SHORT_5, periods=1)


def test_gradient_boosting_requires_min_history():
    with pytest.raises(ValueError, match="at least 6 months"):
        ml_forecasting.gradient_boosting(SHORT_5, periods=1)


def test_random_forest_on_flat_series_forecasts_near_flat_value():
    points = ml_forecasting.random_forest(FLAT_8, periods=2)
    assert len(points) == 2
    assert points[0].period_offset == 1
    assert points[1].period_offset == 2
    for p in points:
        assert p.forecast == pytest.approx(100.0, abs=0.5)
        # a perfectly flat series has zero in-sample residual, so the interval collapses
        assert p.lower_bound == pytest.approx(p.forecast, abs=0.5)
        assert p.upper_bound == pytest.approx(p.forecast, abs=0.5)


def test_gradient_boosting_on_flat_series_forecasts_near_flat_value():
    points = ml_forecasting.gradient_boosting(FLAT_8, periods=1)
    assert points[0].forecast == pytest.approx(100.0, abs=1.0)


def test_random_forest_forecast_stays_in_plausible_range():
    points = ml_forecasting.random_forest(VARIED_10, periods=3)
    assert len(points) == 3
    lo, hi = min(VARIED_10), max(VARIED_10)
    for p in points:
        assert p.forecast > 0
        # tree ensembles predict by averaging leaves seen in training, so they
        # can't extrapolate past the historical range -- forecasts should stay
        # close to (not wildly outside) what's already been observed
        assert lo * 0.7 <= p.forecast <= hi * 1.3
        assert p.lower_bound <= p.forecast <= p.upper_bound


def test_dispatcher_includes_ml_models():
    rf_points = forecasting.forecast(FLAT_8, model="random_forest", periods=1)
    gb_points = forecasting.forecast(FLAT_8, model="gradient_boosting", periods=1)
    assert rf_points[0].forecast == pytest.approx(100.0, abs=0.5)
    assert gb_points[0].forecast == pytest.approx(100.0, abs=1.0)


def test_compare_models_covers_every_registered_model():
    results = forecasting.compare_models(VARIED_10)
    assert set(results.keys()) == set(forecasting.MODELS.keys())
    assert "random_forest" in results
    assert "gradient_boosting" in results
    # with 10 months of history, every model (including the ML ones, which
    # need MIN_ML_HISTORY=6) should have had at least one backtest step it
    # could run, so none should be null
    assert all(v is not None for v in results.values())


def test_compare_models_with_too_little_history_returns_all_none():
    results = forecasting.compare_models(_monthly_series([100.0, 105.0]))
    assert set(results.keys()) == set(forecasting.MODELS.keys())
    assert all(v is None for v in results.values())


def _upload_six_months(client, company_id, sku="ML-WIDGET"):
    rows = "\n".join(f"{sku},Widget,2026-{m:02d},10,{1000 + m * 10},USD" for m in range(1, 7))
    csv_content = f"sku,product_name,period,quantity,amount,currency\n{rows}\n".encode()
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text
    r = client.get(f"/products?company_id={company_id}")
    product = next(p for p in r.json() if p["sku"] == sku)
    return product["id"]


def test_forecast_endpoint_accepts_random_forest_model(client, company):
    company_id = company["id"]
    product_id = _upload_six_months(client, company_id)

    r = client.get(f"/sales/forecast?company_id={company_id}&product_id={product_id}&model=random_forest&periods=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model"] == "random_forest"
    assert len(body["points"]) == 2
    assert body["points"][0]["forecast"] > 0


def test_forecast_endpoint_rejects_ml_model_with_too_little_history(client, company):
    company_id = company["id"]
    csv_content = b"sku,product_name,period,quantity,amount,currency\nSHORT-1,Widget,2026-01,10,1000,USD\n"
    r = client.post(f"/sales/upload?company_id={company_id}", files={"file": ("sales.csv", csv_content, "text/csv")})
    assert r.status_code == 200, r.text
    product_id = next(p for p in client.get(f"/products?company_id={company_id}").json() if p["sku"] == "SHORT-1")["id"]

    r = client.get(f"/sales/forecast?company_id={company_id}&product_id={product_id}&model=random_forest")
    assert r.status_code == 422
    assert "at least 6 months" in r.json()["detail"]


def test_forecast_compare_endpoint(client, company):
    company_id = company["id"]
    product_id = _upload_six_months(client, company_id, sku="ML-COMPARE")

    r = client.get(f"/sales/forecast/compare?company_id={company_id}&product_id={product_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["product_id"] == product_id
    assert body["history_periods"] == 6
    assert set(body["mape_by_model"].keys()) == set(forecasting.MODELS.keys())
