import uuid
from datetime import date

from pydantic import BaseModel


class StatementUploadResult(BaseModel):
    rows_imported: int
    accounts_created: int
    cost_centers_created: int


class IncomeStatementTrendPointOut(BaseModel):
    period: date
    revenue: float
    expense: float
    net_profit: float


class AccountAmountOut(BaseModel):
    gl_account_id: uuid.UUID
    code: str
    name: str
    amount: float


class IncomeStatementOut(BaseModel):
    start_period: date
    end_period: date
    revenue_lines: list[AccountAmountOut]
    total_revenue: float
    expense_lines: list[AccountAmountOut]
    total_expense: float
    net_profit: float


class BalanceSheetOut(BaseModel):
    as_of: date
    asset_lines: list[AccountAmountOut]
    total_assets: float
    liability_lines: list[AccountAmountOut]
    total_liabilities: float
    equity_lines: list[AccountAmountOut]
    total_equity: float
    is_balanced: bool
    difference: float
