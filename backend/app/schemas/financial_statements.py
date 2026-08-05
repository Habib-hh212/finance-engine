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


class CashFlowStatementOut(BaseModel):
    start: date
    end: date
    net_income: float
    depreciation_add_back: float
    increase_in_receivables: float
    increase_in_payables: float
    net_operating_cash_flow: float
    asset_acquisitions: float
    disposal_proceeds: float
    net_investing_cash_flow: float
    net_financing_cash_flow: float
    net_change_in_cash: float
    opening_cash_balance: float
    closing_cash_balance: float
    is_proven: bool
