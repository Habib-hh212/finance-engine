import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class VendorCreate(BaseModel):
    name: str
    state: Optional[str] = None
    gstin: Optional[str] = None


class VendorOut(BaseModel):
    id: uuid.UUID
    name: str
    state: Optional[str] = None
    gstin: Optional[str] = None


class CustomerCreate(BaseModel):
    name: str
    state: Optional[str] = None
    gstin: Optional[str] = None


class CustomerOut(BaseModel):
    id: uuid.UUID
    name: str
    state: Optional[str] = None
    gstin: Optional[str] = None


class CustomerInvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date
    revenue_gl_account_id: uuid.UUID
    net_amount: float
    tax_code_id: Optional[uuid.UUID] = None
    gst_rate_id: Optional[uuid.UUID] = None
    discount_pct: Optional[float] = None
    discount_days: Optional[int] = None
    currency: str = "USD"


class CustomerInvoiceOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    invoice_number: str
    invoice_date: date
    due_date: date
    revenue_gl_account_id: uuid.UUID
    tax_code_id: Optional[uuid.UUID]
    gst_rate_id: Optional[uuid.UUID]
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    discount_pct: Optional[float]
    discount_days: Optional[int]
    discount_taken_amount: Optional[float]
    discount_taken_date: Optional[date]
    amount: float
    currency: str
    status: str
    remaining_balance: float
    journal_entry_id: uuid.UUID


class ClearDocumentIn(BaseModel):
    cash_gl_account_id: uuid.UUID
    cleared_date: date
    take_discount: bool = False


class TakeDiscountIn(BaseModel):
    as_of_date: date


class CustomerReceiptCreate(BaseModel):
    customer_id: uuid.UUID
    receipt_date: date
    cash_gl_account_id: uuid.UUID
    amount: float
    reference: Optional[str] = None


class CustomerReceiptOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    receipt_date: date
    cash_gl_account_id: uuid.UUID
    amount: float
    reference: Optional[str]
    unapplied_balance: float
    journal_entry_id: uuid.UUID


class ApplyReceiptIn(BaseModel):
    receipt_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: float
    applied_date: date


class VendorBillCreate(BaseModel):
    vendor_id: uuid.UUID
    bill_number: str
    bill_date: date
    due_date: date
    expense_gl_account_id: uuid.UUID
    net_amount: float
    tax_code_id: Optional[uuid.UUID] = None
    tds_section_id: Optional[uuid.UUID] = None
    gst_rate_id: Optional[uuid.UUID] = None
    discount_pct: Optional[float] = None
    discount_days: Optional[int] = None
    currency: str = "USD"


class VendorBillOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str
    bill_number: str
    bill_date: date
    due_date: date
    expense_gl_account_id: uuid.UUID
    tax_code_id: Optional[uuid.UUID]
    tds_section_id: Optional[uuid.UUID]
    tds_amount: float
    gst_rate_id: Optional[uuid.UUID]
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    discount_pct: Optional[float]
    discount_days: Optional[int]
    discount_taken_amount: Optional[float]
    discount_taken_date: Optional[date]
    amount: float
    currency: str
    status: str
    remaining_balance: float
    journal_entry_id: uuid.UUID


class VendorPaymentCreate(BaseModel):
    vendor_id: uuid.UUID
    payment_date: date
    cash_gl_account_id: uuid.UUID
    amount: float
    reference: Optional[str] = None


class VendorPaymentOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str
    payment_date: date
    cash_gl_account_id: uuid.UUID
    amount: float
    reference: Optional[str]
    unapplied_balance: float
    journal_entry_id: uuid.UUID


class ApplyPaymentIn(BaseModel):
    payment_id: uuid.UUID
    bill_id: uuid.UUID
    amount: float
    applied_date: date


class AgingRowOut(BaseModel):
    party_id: uuid.UUID
    party_name: str
    document_id: uuid.UUID
    number: str
    due_date: date
    days_overdue: int
    remaining_balance: float
    bucket: str


class AgingReportOut(BaseModel):
    as_of: date
    rows: list[AgingRowOut]
    total_remaining: float
