"""Bank reconciliation: match an uploaded bank statement's transactions
against what's already posted to a cash G/L account, then prove the two
balances agree the standard way -- adjust each side for what the other
doesn't have yet, and confirm the adjusted figures match. Nothing here
posts new journal entries; unmatched bank-only items (a fee, interest)
still need a real posting on the Bookkeeping page, same as any other
transaction -- this module only finds and proves the gap, deliberately.
"""
import io
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import ActualLine, BankStatementLine, GLAccount, JournalEntry, JournalEntryLine
from app.models.bank_reconciliation import MatchType

DATE_TOLERANCE_DAYS = 5
AMOUNT_TOLERANCE = 0.01
REQUIRED_COLUMNS = {"date", "description", "amount"}


class BankReconciliationError(ValueError):
    """Raised when a bank reconciliation transaction violates a rule."""


def _read_table(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    return pd.read_excel(io.BytesIO(file_bytes))


def _cash_account(db: Session, company_id, cash_gl_account_id) -> GLAccount:
    account = db.get(GLAccount, cash_gl_account_id)
    if account is None or account.company_id != company_id:
        raise BankReconciliationError("G/L account not found in this company.")
    return account


@dataclass
class DatedActualLine:
    actual_line_id: object
    amount: float
    effective_date: date
    description: Optional[str]


def _cash_actual_lines(db: Session, company_id, cash_gl_account_id) -> list:
    """Every actual posted to this cash account, paired with the date it
    actually happened on: the journal entry's exact `entry_date` for
    anything routed through the General Ledger (the common case), or the
    period's month-start as an approximation for an actual posted the old
    way, directly on the Controlling page, which only ever recorded a
    month."""
    lines = db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id == cash_gl_account_id).all()
    jel_ids = [line.journal_entry_line_id for line in lines if line.journal_entry_line_id is not None]
    entry_dates: dict = {}
    if jel_ids:
        rows = (
            db.query(JournalEntryLine.id, JournalEntry.entry_date)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .filter(JournalEntryLine.id.in_(jel_ids))
            .all()
        )
        entry_dates = dict(rows)
    return [
        DatedActualLine(
            actual_line_id=line.id,
            amount=float(line.amount),
            effective_date=entry_dates.get(line.journal_entry_line_id, line.period),
            description=line.description,
        )
        for line in lines
    ]


def _already_matched_actual_line_ids(db: Session, company_id, cash_gl_account_id) -> set:
    return {
        row.matched_actual_line_id
        for row in db.query(BankStatementLine)
        .filter(BankStatementLine.company_id == company_id, BankStatementLine.cash_gl_account_id == cash_gl_account_id, BankStatementLine.matched_actual_line_id.isnot(None))
        .all()
    }


@dataclass
class ImportResult:
    rows_imported: int
    auto_matched: int


def import_bank_statement(db: Session, company_id, cash_gl_account_id, file_bytes: bytes, filename: str) -> ImportResult:
    _cash_account(db, company_id, cash_gl_account_id)
    df = _read_table(file_bytes, filename)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise BankReconciliationError(f"File is missing required columns: {sorted(missing)}")

    rows_imported = 0
    for _, row in df.iterrows():
        db.add(
            BankStatementLine(
                company_id=company_id,
                cash_gl_account_id=cash_gl_account_id,
                statement_date=pd.to_datetime(row["date"]).date(),
                description=str(row["description"]),
                amount=round(float(row["amount"]), 2),
                reference=str(row["reference"]) if "reference" in df.columns and pd.notna(row.get("reference")) else None,
            )
        )
        rows_imported += 1
    db.commit()

    auto_matched = auto_match(db, company_id, cash_gl_account_id)
    return ImportResult(rows_imported=rows_imported, auto_matched=auto_matched)


def auto_match(db: Session, company_id, cash_gl_account_id) -> int:
    """Auto-matches only when exactly one candidate actual line has the
    same amount within the date-tolerance window -- an ambiguous case (two
    equally-plausible candidates) is deliberately left for a human to
    match by hand rather than guessed at, since matching the wrong
    transaction is worse than matching nothing."""
    unmatched_bank_lines = (
        db.query(BankStatementLine)
        .filter(BankStatementLine.company_id == company_id, BankStatementLine.cash_gl_account_id == cash_gl_account_id, BankStatementLine.matched_actual_line_id.is_(None))
        .all()
    )
    if not unmatched_bank_lines:
        return 0

    already_used = _already_matched_actual_line_ids(db, company_id, cash_gl_account_id)
    actual_lines = [a for a in _cash_actual_lines(db, company_id, cash_gl_account_id) if a.actual_line_id not in already_used]

    matched_count = 0
    for bank_line in unmatched_bank_lines:
        candidates = [
            a
            for a in actual_lines
            if abs(a.amount - float(bank_line.amount)) <= AMOUNT_TOLERANCE and abs((a.effective_date - bank_line.statement_date).days) <= DATE_TOLERANCE_DAYS
        ]
        if len(candidates) == 1:
            match = candidates[0]
            bank_line.matched_actual_line_id = match.actual_line_id
            bank_line.match_type = MatchType.AUTO
            actual_lines.remove(match)
            matched_count += 1

    db.commit()
    return matched_count


def manual_match(db: Session, bank_line: BankStatementLine, actual_line_id) -> BankStatementLine:
    if bank_line.matched_actual_line_id is not None:
        raise BankReconciliationError("This bank line is already matched -- unmatch it first.")
    actual_line = db.get(ActualLine, actual_line_id)
    if actual_line is None or actual_line.company_id != bank_line.company_id or actual_line.gl_account_id != bank_line.cash_gl_account_id:
        raise BankReconciliationError("That actual doesn't belong to this cash account.")
    already_used = _already_matched_actual_line_ids(db, bank_line.company_id, bank_line.cash_gl_account_id)
    if actual_line_id in already_used:
        raise BankReconciliationError("That actual is already matched to another bank line.")

    bank_line.matched_actual_line_id = actual_line_id
    bank_line.match_type = MatchType.MANUAL
    db.commit()
    db.refresh(bank_line)
    return bank_line


def unmatch(db: Session, bank_line: BankStatementLine) -> BankStatementLine:
    if bank_line.matched_actual_line_id is None:
        raise BankReconciliationError("This bank line isn't matched.")
    bank_line.matched_actual_line_id = None
    bank_line.match_type = None
    db.commit()
    db.refresh(bank_line)
    return bank_line


def delete_bank_line(db: Session, bank_line: BankStatementLine) -> None:
    if bank_line.matched_actual_line_id is not None:
        raise BankReconciliationError("Can't delete a matched bank line -- unmatch it first.")
    db.delete(bank_line)
    db.commit()


@dataclass
class UnmatchedGLLine:
    actual_line_id: object
    amount: float
    effective_date: date
    description: Optional[str]


def unmatched_gl_lines(db: Session, company_id, cash_gl_account_id) -> list:
    already_used = _already_matched_actual_line_ids(db, company_id, cash_gl_account_id)
    return [
        UnmatchedGLLine(actual_line_id=a.actual_line_id, amount=a.amount, effective_date=a.effective_date, description=a.description)
        for a in _cash_actual_lines(db, company_id, cash_gl_account_id)
        if a.actual_line_id not in already_used
    ]


@dataclass
class ReconciliationSummary:
    as_of: date
    book_balance: float
    bank_statement_ending_balance: float
    unmatched_bank_lines_total: float
    unmatched_gl_lines_total: float
    adjusted_book_balance: float
    adjusted_bank_balance: float
    is_reconciled: bool


def reconciliation_summary(db: Session, company_id, cash_gl_account_id, as_of: date, bank_statement_ending_balance: float) -> ReconciliationSummary:
    _cash_account(db, company_id, cash_gl_account_id)
    book_balance = round(
        sum(float(line.amount) for line in db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id == cash_gl_account_id, ActualLine.period <= as_of).all()),
        2,
    )

    unmatched_bank = (
        db.query(BankStatementLine)
        .filter(
            BankStatementLine.company_id == company_id,
            BankStatementLine.cash_gl_account_id == cash_gl_account_id,
            BankStatementLine.matched_actual_line_id.is_(None),
            BankStatementLine.statement_date <= as_of,
        )
        .all()
    )
    unmatched_bank_total = round(sum(float(line.amount) for line in unmatched_bank), 2)

    gl_lines = [line for line in unmatched_gl_lines(db, company_id, cash_gl_account_id) if line.effective_date <= as_of]
    unmatched_gl_total = round(sum(line.amount for line in gl_lines), 2)

    adjusted_book_balance = round(book_balance + unmatched_bank_total, 2)
    adjusted_bank_balance = round(bank_statement_ending_balance + unmatched_gl_total, 2)

    return ReconciliationSummary(
        as_of=as_of,
        book_balance=book_balance,
        bank_statement_ending_balance=round(bank_statement_ending_balance, 2),
        unmatched_bank_lines_total=unmatched_bank_total,
        unmatched_gl_lines_total=unmatched_gl_total,
        adjusted_book_balance=adjusted_book_balance,
        adjusted_bank_balance=adjusted_bank_balance,
        is_reconciled=abs(adjusted_book_balance - adjusted_bank_balance) <= AMOUNT_TOLERANCE,
    )
