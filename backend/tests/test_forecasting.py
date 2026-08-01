import pandas as pd
import pytest

from app.services import forecasting

# Flat series: every model should forecast ~100 with a tight interval.
FLAT_SERIES = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0])

# Trending series: 100, 110, 120, 130, 140 (+10/month, zero noise around the trend).
TRENDING_SERIES = pd.Series([100.0, 110.0, 120.0, 130.0, 140.0])

# Volatile series: same mean-ish level as FLAT_SERIES but noisy month to month.
VOLATILE_SERIES = pd.Series([100.0, 140.0, 90.0, 150.0, 80.0])


def test_moving_average_flat_series():
    points = forecasting.moving_average(FLAT_SERIES, periods=2, window=3)
    assert len(points) == 2
    assert points[0].forecast == 100.0
    assert points[0].lower_bound == points[0].upper_bound == 100.0


def test_weighted_average_favors_recent_values():
    points = forecasting.weighted_average(TRENDING_SERIES, periods=1, window=3)
    # weighted average of last 3 (120, 130, 140) with weights 1,2,3 => (120+260+420)/6 = 133.33
    assert points[0].forecast == pytest.approx(133.33, abs=0.1)
    # and it should sit above the plain mean of those three (125), since it favors the latest, higher values
    assert points[0].forecast > 125.0


def test_exponential_smoothing_flat_series():
    points = forecasting.exponential_smoothing(FLAT_SERIES, periods=1, alpha=0.5)
    assert points[0].forecast == 100.0


def test_exponential_smoothing_tracks_trend_upward():
    points = forecasting.exponential_smoothing(TRENDING_SERIES, periods=1, alpha=0.5)
    assert points[0].forecast > 100.0
    assert points[0].forecast < 140.0


def test_confidence_interval_widens_with_volatility():
    flat_points = forecasting.moving_average(FLAT_SERIES, periods=1)
    volatile_points = forecasting.moving_average(VOLATILE_SERIES, periods=1)
    flat_width = flat_points[0].upper_bound - flat_points[0].lower_bound
    volatile_width = volatile_points[0].upper_bound - volatile_points[0].lower_bound
    assert volatile_width > flat_width


def test_confidence_interval_is_zero_for_noiseless_trend():
    # A perfectly linear trend has constant month-over-month deltas, so the
    # diff-based residual (noise around the trend) is legitimately zero.
    points = forecasting.moving_average(TRENDING_SERIES, periods=1)
    assert points[0].lower_bound == points[0].upper_bound == points[0].forecast


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        forecasting.forecast(FLAT_SERIES, model="not_a_model")


def test_empty_history_raises():
    with pytest.raises(ValueError):
        forecasting.moving_average(pd.Series([], dtype=float), periods=1)
