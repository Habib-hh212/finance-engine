import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

GLForecastRole = Literal["cash", "accounts_receivable", "accounts_payable", "tds_payable"]


class GLAccountCreate(BaseModel):
    code: str
    name: str
    category: Literal["revenue", "expense", "asset", "liability", "equity"]
    forecast_role: Optional[GLForecastRole] = None


class GLAccountUpdate(BaseModel):
    forecast_role: Optional[GLForecastRole] = None


class GLAccountOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str
    forecast_role: Optional[str] = None

    model_config = {"from_attributes": True}


BudgetType = Literal["revenue", "expense", "master", "zero_based", "flexible", "rolling", "capital"]


class BudgetCreate(BaseModel):
    name: str
    type: BudgetType
    fiscal_year: int
    currency: str = "USD"
    rolling_window_months: Optional[int] = None  # only meaningful when type == "rolling"; defaults to 12


class BudgetLineIn(BaseModel):
    gl_account_id: uuid.UUID
    period: date
    amount: float
    currency: Optional[str] = None  # defaults to the budget's currency if omitted
    justification: Optional[str] = None
    variable_rate_per_unit: Optional[float] = None
    useful_life_years: Optional[int] = None
    annual_cash_flow: Optional[float] = None
    cost_center_id: Optional[uuid.UUID] = None


class BudgetLineUpdate(BaseModel):
    gl_account_id: Optional[uuid.UUID] = None
    period: Optional[date] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    justification: Optional[str] = None
    variable_rate_per_unit: Optional[float] = None
    useful_life_years: Optional[int] = None
    annual_cash_flow: Optional[float] = None
    cost_center_id: Optional[uuid.UUID] = None


class BudgetLineOut(BaseModel):
    id: uuid.UUID
    gl_account_id: uuid.UUID
    period: date
    amount: float
    currency: str
    justification: Optional[str] = None
    variable_rate_per_unit: Optional[float] = None
    useful_life_years: Optional[int] = None
    annual_cash_flow: Optional[float] = None
    cost_center_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class CostCenterCreate(BaseModel):
    code: str
    name: str
    manager_name: Optional[str] = None


class CostCenterOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    manager_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ApprovalOut(BaseModel):
    role: str
    action: str
    actor_name: str
    comment: Optional[str]
    acted_at: datetime

    model_config = {"from_attributes": True}


class BudgetOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    type: str
    fiscal_year: int
    currency: str
    status: str
    rolling_window_months: Optional[int] = None

    model_config = {"from_attributes": True}


class BudgetDetail(BudgetOut):
    lines: list[BudgetLineOut]
    approvals: list[ApprovalOut]


class ApprovalAction(BaseModel):
    actor_name: str
    comment: Optional[str] = None


class BudgetVersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    submitted_at: datetime
    lines_snapshot: list[dict]

    model_config = {"from_attributes": True}
