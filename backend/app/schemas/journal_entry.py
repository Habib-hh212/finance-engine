import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class JournalEntryLineIn(BaseModel):
    gl_account_id: uuid.UUID
    debit_amount: float = 0
    credit_amount: float = 0
    cost_center_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    tax_code_id: Optional[uuid.UUID] = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    reference: Optional[str] = None
    description: Optional[str] = None
    currency: str = "USD"
    lines: list[JournalEntryLineIn]


class ReverseJournalEntryIn(BaseModel):
    entry_date: date


class JournalEntryLineOut(BaseModel):
    id: uuid.UUID
    gl_account_id: uuid.UUID
    gl_account_code: str
    gl_account_name: str
    cost_center_id: Optional[uuid.UUID]
    debit_amount: float
    credit_amount: float
    description: Optional[str]
    tax_code_id: Optional[uuid.UUID] = None
    tax_code: Optional[str] = None
    tax_amount: Optional[float] = None


class JournalEntryOut(BaseModel):
    id: uuid.UUID
    entry_date: date
    reference: Optional[str]
    description: Optional[str]
    currency: str
    status: str
    reverses_entry_id: Optional[uuid.UUID]
    created_at: datetime
    posted_at: Optional[datetime]
    lines: list[JournalEntryLineOut]


class TrialBalanceRowOut(BaseModel):
    gl_account_id: uuid.UUID
    gl_account_code: str
    gl_account_name: str
    category: str
    total_debit: float
    total_credit: float
    net_balance: float


class TrialBalanceOut(BaseModel):
    as_of: date
    rows: list[TrialBalanceRowOut]
    total_debit: float
    total_credit: float
    is_balanced: bool


class GLLedgerLineOut(BaseModel):
    journal_entry_id: uuid.UUID
    journal_entry_line_id: uuid.UUID
    entry_date: date
    reference: Optional[str]
    description: Optional[str]
    debit_amount: float
    credit_amount: float
    running_balance: float


class GLLedgerOut(BaseModel):
    gl_account_id: uuid.UUID
    gl_account_code: str
    gl_account_name: str
    category: str
    start: date
    end: date
    opening_balance: float
    closing_balance: float
    lines: list[GLLedgerLineOut]
