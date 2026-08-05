import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class BankImportResultOut(BaseModel):
    rows_imported: int
    auto_matched: int


class BankStatementLineOut(BaseModel):
    id: uuid.UUID
    cash_gl_account_id: uuid.UUID
    statement_date: date
    description: str
    amount: float
    reference: Optional[str]
    matched_actual_line_id: Optional[uuid.UUID]
    match_type: Optional[str]


class ManualMatchIn(BaseModel):
    actual_line_id: uuid.UUID


class UnmatchedGLLineOut(BaseModel):
    actual_line_id: uuid.UUID
    amount: float
    effective_date: date
    description: Optional[str]


class ReconciliationSummaryOut(BaseModel):
    as_of: date
    book_balance: float
    bank_statement_ending_balance: float
    unmatched_bank_lines_total: float
    unmatched_gl_lines_total: float
    adjusted_book_balance: float
    adjusted_bank_balance: float
    is_reconciled: bool
