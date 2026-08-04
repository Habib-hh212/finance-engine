"""Monte Carlo forecast simulation: runs many random trials on top of the
existing point-forecast models to produce a p10/p50/p90 band per period,
instead of the single fixed-width confidence interval `forecasting.py`'s
`_confidence_interval` already gives (same +/- margin at every horizon,
regardless of how far out the period is).

The shock at each period is drawn from the same source `forecasting.py`
already uses to size its confidence interval -- the standard deviation of
period-over-period changes in the actual history (`history.diff().std()`)
-- but instead of applying it once as a static +/- band, this compounds an
independent random shock onto each trial's running path (`np.cumsum`), so
uncertainty genuinely widens further into the future the way a real
multi-period financial projection's would, rather than staying a constant
width forecast after forecast.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from app.services import forecasting

DEFAULT_TRIALS = 1000
MIN_HISTORY = 2


@dataclass
class MonteCarloPoint:
    period_offset: int
    p10: float
    p50: float
    p90: float
    mean: float


def simulate(
    history: pd.Series,
    model: str,
    periods: int,
    trials: int = DEFAULT_TRIALS,
    seed: Optional[int] = None,
) -> list[MonteCarloPoint]:
    if len(history) < MIN_HISTORY:
        raise ValueError(f"Need at least {MIN_HISTORY} periods of history to estimate volatility for a simulation")

    point_forecasts = forecasting.forecast(history, model=model, periods=periods)
    residual_std = history.diff().dropna().std()
    if pd.isna(residual_std):
        residual_std = 0.0

    rng = np.random.default_rng(seed)
    shocks = rng.normal(loc=0.0, scale=float(residual_std), size=(trials, periods))
    cumulative_shocks = np.cumsum(shocks, axis=1)

    base = np.array([p.forecast for p in point_forecasts])
    paths = np.maximum(base[np.newaxis, :] + cumulative_shocks, 0.0)

    results = []
    for i in range(periods):
        column = paths[:, i]
        results.append(
            MonteCarloPoint(
                period_offset=i + 1,
                p10=round(float(np.percentile(column, 10)), 2),
                p50=round(float(np.percentile(column, 50)), 2),
                p90=round(float(np.percentile(column, 90)), 2),
                mean=round(float(column.mean()), 2),
            )
        )
    return results
