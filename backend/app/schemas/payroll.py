import uuid
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

TaxRegimeLiteral = Literal["old", "new"]


class EmployeeCreate(BaseModel):
    name: str
    pan: Optional[str] = None
    email: Optional[str] = None
    date_of_joining: date
    tax_regime: TaxRegimeLiteral = "new"
    basic_monthly: float
    hra_monthly: float = 0.0
    special_allowance_monthly: float = 0.0
    other_allowance_monthly: float = 0.0
    is_metro: bool = False


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    pan: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    tax_regime: Optional[TaxRegimeLiteral] = None
    basic_monthly: Optional[float] = None
    hra_monthly: Optional[float] = None
    special_allowance_monthly: Optional[float] = None
    other_allowance_monthly: Optional[float] = None
    is_metro: Optional[bool] = None


class EmployeeOut(BaseModel):
    id: uuid.UUID
    name: str
    pan: Optional[str]
    email: Optional[str]
    date_of_joining: date
    is_active: bool
    tax_regime: str
    basic_monthly: float
    hra_monthly: float
    special_allowance_monthly: float
    other_allowance_monthly: float
    is_metro: bool

    model_config = {"from_attributes": True}


class InvestmentDeclarationCreate(BaseModel):
    financial_year: int
    section_80c: float = 0.0
    section_80d: float = 0.0
    home_loan_interest: float = 0.0
    rent_paid_monthly: float = 0.0


class InvestmentDeclarationOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    financial_year: int
    section_80c: float
    section_80d: float
    home_loan_interest: float
    rent_paid_monthly: float

    model_config = {"from_attributes": True}


class PayrollRunCreate(BaseModel):
    period_month: int
    period_year: int
    cash_gl_account_id: uuid.UUID
    run_date: date


class PayslipOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    basic: float
    hra: float
    special_allowance: float
    other_allowance: float
    gross_pay: float
    pf_employee: float
    pf_employer: float
    esi_employee: float
    esi_employer: float
    professional_tax: float
    tds_amount: float
    net_pay: float

    model_config = {"from_attributes": True}


class PayrollRunOut(BaseModel):
    id: uuid.UUID
    period_month: int
    period_year: int
    run_date: date
    status: str
    journal_entry_id: Optional[uuid.UUID]
    payslips: list[PayslipOut]

    model_config = {"from_attributes": True}


class Form16MonthRowOut(BaseModel):
    period_month: int
    period_year: int
    gross_pay: float
    tds_amount: float


class Form16SummaryOut(BaseModel):
    employee_id: uuid.UUID
    financial_year: int
    regime: str
    total_gross: float
    total_tds: float
    months: list[Form16MonthRowOut]
