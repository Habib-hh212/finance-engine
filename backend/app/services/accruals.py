from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Accrual, JournalEntry
from app.services import bookkeeping


class AccrualError(ValueError):
    """Raised when an accrual transaction violates a rule."""


def create_accrual(
    db: Session,
    company_id,
    entry_date: date,
    debit_gl_account_id,
    credit_gl_account_id,
    amount: float,
    reversal_date: date,
    reference: Optional[str] = None,
    description: Optional[str] = None,
) -> Accrual:
    if amount <= 0:
        raise AccrualError("Accrual amount must be positive.")
    if reversal_date <= entry_date:
        raise AccrualError("The reversal date must be after the entry date.")

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        entry_date,
        [
            bookkeeping.LineInput(gl_account_id=debit_gl_account_id, debit_amount=amount, description=description),
            bookkeeping.LineInput(gl_account_id=credit_gl_account_id, credit_amount=amount, description=description),
        ],
        reference=reference,
        description=description,
        currency="USD",
    )
    entry = bookkeeping.post_journal_entry(db, entry)

    accrual = Accrual(company_id=company_id, journal_entry_id=entry.id, reversal_date=reversal_date)
    db.add(accrual)
    db.commit()
    db.refresh(accrual)
    return accrual


def reverse_accrual(db: Session, accrual: Accrual) -> Accrual:
    if accrual.reversed:
        raise AccrualError("This accrual has already been reversed.")
    original = db.get(JournalEntry, accrual.journal_entry_id)
    reversal = bookkeeping.reverse_journal_entry(db, original, accrual.reversal_date)
    accrual.reversed = True
    accrual.reversal_journal_entry_id = reversal.id
    db.commit()
    db.refresh(accrual)
    return accrual
