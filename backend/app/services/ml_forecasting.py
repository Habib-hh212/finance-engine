"""ML-based sales forecasting: Random Forest and Gradient Boosting
regressors from scikit-learn, forecasting multiple steps ahead
recursively from lag/rolling/seasonal features built off monthly
history.

Chosen over XGBoost/Prophet/LSTM specifically for hosting reasons: this
backend runs as a Vercel serverless function with tight package-size and
cold-start limits. XGBoost carries a large native binary, and Prophet
(cmdstanpy) and LSTM (TensorFlow/PyTorch) each drag in a full
probabilistic-programming or deep-learning stack -- scikit-learn is the
one of the four that reliably fits.

Needs at least MIN_ML_HISTORY data points before it'll produce a
forecast. A forest fit on a handful of rows is closer to noise than to a
signal, so below that threshold this raises ValueError rather than
returning a confident-looking, meaningless number -- the same contract
the statistical models in forecasting.py already follow for empty
history.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from app.services.forecasting import ForecastPoint

MIN_ML_HISTORY = 6
LOOKBACK = 3


def _row_features(values: list[float], months: list[int], i: int) -> list[float]:
    """Features for predicting values[i] (or, for forecasting, the next
    unseen point) from the LOOKBACK points immediately before it: the lags
    themselves (most recent first), their rolling mean, a plain time index
    (captures trend), and the target month as sin/cos (so December and
    January read as adjacent, not eleven apart)."""
    lags = list(reversed(values[i - LOOKBACK : i]))
    rolling_mean = sum(values[i - LOOKBACK : i]) / LOOKBACK
    month = months[i]
    month_sin = np.sin(2 * np.pi * month / 12)
    month_cos = np.cos(2 * np.pi * month / 12)
    return [*lags, rolling_mean, i, month_sin, month_cos]


def _build_training_set(values: list[float], months: list[int]) -> tuple[np.ndarray, np.ndarray]:
    X = [_row_features(values, months, i) for i in range(LOOKBACK, len(values))]
    y = values[LOOKBACK:]
    return np.array(X), np.array(y)


def _forecast_recursive(model, values: list[float], months: list[int], periods: int) -> list[float]:
    values = list(values)
    months = list(months)
    forecasts = []
    for _ in range(periods):
        next_month = (months[-1] % 12) + 1
        # a placeholder month entry lets _row_features address "the point we're about to predict"
        months.append(next_month)
        x = np.array([_row_features(values, months, len(values))])
        pred = float(model.predict(x)[0])
        forecasts.append(pred)
        values.append(pred)
    return forecasts


def _fit_and_forecast(history: pd.Series, periods: int, model_cls, **model_kwargs) -> list[ForecastPoint]:
    if len(history) < MIN_ML_HISTORY:
        raise ValueError(f"Need at least {MIN_ML_HISTORY} months of history for an ML forecast, got {len(history)}")

    values = [float(v) for v in history.to_numpy()]
    months = [d.month for d in history.index]
    X, y = _build_training_set(values, months)

    model = model_cls(**model_kwargs)
    model.fit(X, y)

    # In-sample residuals drive the confidence interval -- the same convention
    # forecasting.py's statistical models use (95% via a 1.96 z-multiplier).
    residuals = y - model.predict(X)
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.0
    margin = 1.96 * residual_std

    point_forecasts = _forecast_recursive(model, values, months, periods)
    return [
        ForecastPoint(
            period_offset=i + 1,
            forecast=round(point, 2),
            lower_bound=round(max(point - margin, 0.0), 2),
            upper_bound=round(point + margin, 2),
        )
        for i, point in enumerate(point_forecasts)
    ]


def random_forest(history: pd.Series, periods: int = 3) -> list[ForecastPoint]:
    return _fit_and_forecast(history, periods, RandomForestRegressor, n_estimators=200, max_depth=4, random_state=42)


def gradient_boosting(history: pd.Series, periods: int = 3) -> list[ForecastPoint]:
    return _fit_and_forecast(
        history, periods, GradientBoostingRegressor, n_estimators=200, max_depth=3, learning_rate=0.1, random_state=42
    )
