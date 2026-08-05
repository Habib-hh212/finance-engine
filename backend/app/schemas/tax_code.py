import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class TaxCodeCreate(BaseModel):
    country: str
    code: str
    name: str
    tax_type: str
    rate_pct: float
    direction: str
    gl_account_id: uuid.UUID


class TaxCodeUpdate(BaseModel):
    name: Optional[str] = None
    rate_pct: Optional[float] = None
    is_active: Optional[bool] = None


class TaxCodeOut(BaseModel):
    id: uuid.UUID
    country: str
    code: str
    name: str
    tax_type: str
    rate_pct: float
    direction: str
    gl_account_id: uuid.UUID
    gl_account_code: str
    gl_account_name: str
    is_active: bool


class TaxReportRowOut(BaseModel):
    tax_code_id: uuid.UUID
    code: str
    name: str
    country: str
    tax_type: str
    direction: str
    rate_pct: float
    taxable_base: float
    tax_amount: float


class TaxReportOut(BaseModel):
    start: date
    end: date
    rows: list[TaxReportRowOut]
    total_output_tax: float
    total_input_tax: float
    net_tax_payable: float
