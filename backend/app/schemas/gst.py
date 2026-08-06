import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class GstRateCreate(BaseModel):
    description: str
    rate_pct: float
    direction: str
    cgst_gl_account_id: uuid.UUID
    sgst_gl_account_id: uuid.UUID
    igst_gl_account_id: uuid.UUID


class GstRateUpdate(BaseModel):
    description: Optional[str] = None
    rate_pct: Optional[float] = None
    is_active: Optional[bool] = None


class GstRateOut(BaseModel):
    id: uuid.UUID
    description: str
    rate_pct: float
    direction: str
    cgst_gl_account_id: uuid.UUID
    sgst_gl_account_id: uuid.UUID
    igst_gl_account_id: uuid.UUID
    is_active: bool

    model_config = {"from_attributes": True}


class Gstr1B2BRowOut(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_name: str
    customer_gstin: str
    taxable_value: float
    rate_pct: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    invoice_value: float


class Gstr1B2CRowOut(BaseModel):
    place_of_supply: str
    rate_pct: float
    taxable_value: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float


class Gstr1HsnRowOut(BaseModel):
    hsn_sac_code: str
    taxable_value: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float


class Gstr1Out(BaseModel):
    start: date
    end: date
    b2b_rows: list[Gstr1B2BRowOut]
    b2c_rows: list[Gstr1B2CRowOut]
    hsn_rows: list[Gstr1HsnRowOut]
    total_taxable_value: float
    total_tax: float


class Gstr3bOut(BaseModel):
    start: date
    end: date
    outward_taxable_value: float
    output_cgst: float
    output_sgst: float
    output_igst: float
    inward_taxable_value: float
    input_cgst: float
    input_sgst: float
    input_igst: float
    net_cgst_payable: float
    net_sgst_payable: float
    net_igst_payable: float
    net_tax_payable: float
