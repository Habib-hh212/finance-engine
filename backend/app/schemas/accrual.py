import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class AccrualCreate(BaseModel):
    entry_date: date
    debit_gl_account_id: uuid.UUID
    credit_gl_account_id: uuid.UUID
    amount: float
    reversal_date: date
    reference: Optional[str] = None
    description: Optional[str] = None


class AccrualOut(BaseModel):
    id: uuid.UUID
    journal_entry_id: uuid.UUID
    entry_date: date
    reference: Optional[str]
    description: Optional[str]
    amount: float
    debit_gl_account_id: uuid.UUID
    debit_gl_account_code: str
    credit_gl_account_id: uuid.UUID
    credit_gl_account_code: str
    reversal_date: date
    reversed: bool
    reversal_journal_entry_id: Optional[uuid.UUID]
    due_for_reversal: bool
