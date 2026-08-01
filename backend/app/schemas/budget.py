import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class GLAccountCreate(BaseModel):
    code: str
    name: str
    category: Literal["revenue", "expense"]


class GLAccountOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str

    model_config = {"from_attributes": True}


class BudgetCreate(BaseModel):
    name: str
    type: Literal["revenue", "expense", "master"]
    fiscal_year: int
    currency: str = "USD"


class BudgetLineIn(BaseModel):
    gl_account_id: uuid.UUID
    period: date
    amount: float
    currency: Optional[str] = None  # defaults to the budget's currency if omitted


class BudgetLineOut(BaseModel):
    id: uuid.UUID
    gl_account_id: uuid.UUID
    period: date
    amount: float
    currency: str

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

    model_config = {"from_attributes": True}


class BudgetDetail(BudgetOut):
    lines: list[BudgetLineOut]
    approvals: list[ApprovalOut]


class ApprovalAction(BaseModel):
    actor_name: str
    comment: Optional[str] = None
