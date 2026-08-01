"""Phase 1 forecast models: moving average, weighted average, exponential smoothing.

Each function takes a pandas Series of historical monthly values (indexed by
month, oldest first) and returns a forecast for the next `periods` months
with a 95% confidence interval derived from historical residual error.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ForecastPoint:
    period_offset: int
    forecast: float
    lower_bound: float
    upper_bound: float


def _confidence_interval(history: pd.Series, point_forecast: float, z: float = 1.96) -> tuple[float, float]:
    if len(history) < 2:
        return point_forecast, point_forecast
    residual_std = history.diff().dropna().std()
    if pd.isna(residual_std):
        residual_std = 0.0
    margin = z * residual_std
    return max(point_forecast - margin, 0.0), point_forecast + margin


def moving_average(history: pd.Series, periods: int = 3, window: int = 3) -> list[ForecastPoint]:
    if len(history) == 0:
        raise ValueError("history must contain at least one period")
    window = min(window, len(history))
    point = history.tail(window).mean()
    lower, upper = _confidence_interval(history, point)
    return [ForecastPoint(i + 1, round(point, 2), round(lower, 2), round(upper, 2)) for i in range(periods)]


def weighted_average(history: pd.Series, periods: int = 3, window: int = 3) -> list[ForecastPoint]:
    if len(history) == 0:
        raise ValueError("history must contain at least one period")
    window = min(window, len(history))
    recent = history.tail(window)
    weights = np.arange(1, window + 1)
    point = float(np.average(recent, weights=weights))
    lower, upper = _confidence_interval(history, point)
    return [ForecastPoint(i + 1, round(point, 2), round(lower, 2), round(upper, 2)) for i in range(periods)]


def exponential_smoothing(history: pd.Series, periods: int = 3, alpha: float = 0.3) -> list[ForecastPoint]:
    if len(history) == 0:
        raise ValueError("history must contain at least one period")
    level = history.iloc[0]
    for value in history.iloc[1:]:
        level = alpha * value + (1 - alpha) * level
    lower, upper = _confidence_interval(history, level)
    return [ForecastPoint(i + 1, round(level, 2), round(lower, 2), round(upper, 2)) for i in range(periods)]


MODELS = {
    "moving_average": moving_average,
    "weighted_average": weighted_average,
    "exponential_smoothing": exponential_smoothing,
}


def forecast(history: pd.Series, model: str, periods: int = 3) -> list[ForecastPoint]:
    if model not in MODELS:
        raise ValueError(f"Unknown model '{model}'. Choose from {list(MODELS)}")
    return MODELS[model](history, periods=periods)
