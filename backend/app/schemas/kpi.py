from typing import Optional

from pydantic import BaseModel


class KPIResponse(BaseModel):
    gross_margin_pct: Optional[float]
    budget_utilization_pct: Optional[float]
    forecast_accuracy_mape: Optional[float]
    cash_runway_months: Optional[int]
