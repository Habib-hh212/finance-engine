import uuid
from typing import Optional

from pydantic import BaseModel

from app.schemas.statement_forecast import BalanceSheetForecastPeriodOut, IncomeStatementForecastPeriodOut


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sales_growth_pct: float = 0.0
    expense_growth_pct: float = 0.0


class ScenarioOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    sales_growth_pct: float
    expense_growth_pct: float

    model_config = {"from_attributes": True}


class ScenarioForecastOut(BaseModel):
    scenario: ScenarioOut
    base_income_statement: list[IncomeStatementForecastPeriodOut]
    scenario_income_statement: list[IncomeStatementForecastPeriodOut]
    base_balance_sheet: list[BalanceSheetForecastPeriodOut]
    scenario_balance_sheet: list[BalanceSheetForecastPeriodOut]
