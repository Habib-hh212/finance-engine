from datetime import date

from pydantic import BaseModel


class IncomeStatementForecastPeriodOut(BaseModel):
    period: date
    revenue_forecast: float
    expense_forecast: float
    net_profit_forecast: float


class BalanceSheetForecastPeriodOut(BaseModel):
    period: date
    accounts_receivable: float
    cash: float
    other_assets: float
    total_assets: float
    accounts_payable: float
    other_liabilities: float
    total_liabilities: float
    equity: float
    is_balanced: bool
    difference: float
