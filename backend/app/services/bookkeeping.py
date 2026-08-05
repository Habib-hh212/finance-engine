"""Double-entry bookkeeping: journal entries that must balance (total debits
== total credits) before they can be posted -- the one rule the rest of this
system has never enforced. `ActualLine` (used by Cost Controlling, the
Financial Statements, KPIs, the Dashboard charts) is just a single amount
against one account with no counterpart requirement.

A posted entry's lines are mirrored into `ActualLine` (tagged via
`journal_entry_line_id`), signed by each account's normal-balance direction,
so every existing report that already sums `ActualLine` picks up
double-entry-verified postings automatically -- with zero changes to any of
those modules. The direct "Post an actual" quick-entry on the Controlling
page still works exactly as before; this is an additional, more rigorous
front door, not a replacement for it.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ActualLine, GLAccount, JournalEntry, JournalEntryLine
from app.models.journal_entry import JournalEntryStatus

BALANCE_TOLERANCE = 0.01

# Categories whose balance normally increases on the debit side (assets,
# expenses). Everything else -- revenue, liability, equity -- normally
# increases on the credit side. This is the textbook accounting-equation
# rule (Assets = Liabilities + Equity), not a design choice, and it's what
# lets a posted journal line become a correctly-signed ActualLine.amount
# that matches what a manual "post an actual" entry would already look
# like for that same real-world event.
DEBIT_NORMAL_CATEGORIES = {"asset", "expense"}


class JournalEntryError(ValueError):
    """Raised when an entry violates a double-entry bookkeeping rule."""


def _signed_amount(category: str, debit_amount: float, credit_amount: float) -> float:
    if category in DEBIT_NORMAL_CATEGORIES:
        return round(debit_amount - credit_amount, 2)
    return round(credit_amount - debit_amount, 2)


@dataclass
class LineInput:
    gl_account_id: object
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    cost_center_id: Optional[object] = None
    description: Optional[str] = None


def create_journal_entry(
    db: Session,
    company_id,
    entry_date: date,
    lines: list[LineInput],
    reference: Optional[str] = None,
    description: Optional[str] = None,
    currency: str = "USD",
) -> JournalEntry:
    if len(lines) < 2:
        raise JournalEntryError("A journal entry needs at least two lines -- a debit and a credit somewhere.")

    accounts = {a.id for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    total_debit = 0.0
    total_credit = 0.0
    for line in lines:
        if line.gl_account_id not in accounts:
            raise JournalEntryError("A line references a GL account that doesn't belong to this company.")
        if line.debit_amount and line.credit_amount:
            raise JournalEntryError("A line can't be both a debit and a credit -- split it into two lines.")
        if not line.debit_amount and not line.credit_amount:
            raise JournalEntryError("Every line needs either a debit or a credit amount.")
        if line.debit_amount < 0 or line.credit_amount < 0:
            raise JournalEntryError("Debit and credit amounts can't be negative.")
        total_debit += line.debit_amount
        total_credit += line.credit_amount

    if abs(total_debit - total_credit) > BALANCE_TOLERANCE:
        raise JournalEntryError(
            f"Entry doesn't balance: total debits {total_debit:.2f} does not equal total credits {total_credit:.2f}."
        )

    entry = JournalEntry(
        company_id=company_id,
        entry_date=entry_date,
        reference=reference,
        description=description,
        currency=currency,
        status=JournalEntryStatus.DRAFT,
    )
    db.add(entry)
    db.flush()

    for line in lines:
        db.add(
            JournalEntryLine(
                journal_entry_id=entry.id,
                gl_account_id=line.gl_account_id,
                cost_center_id=line.cost_center_id,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                description=line.description,
            )
        )
    db.commit()
    db.refresh(entry)
    return entry


def post_journal_entry(db: Session, entry: JournalEntry) -> JournalEntry:
    if entry.status != JournalEntryStatus.DRAFT:
        raise JournalEntryError(f"Only a draft entry can be posted (this one is '{entry.status}').")

    lines = db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id == entry.id).all()
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == entry.company_id).all()}

    for line in lines:
        account = accounts[line.gl_account_id]
        signed = _signed_amount(account.category, float(line.debit_amount), float(line.credit_amount))
        db.add(
            ActualLine(
                company_id=entry.company_id,
                gl_account_id=line.gl_account_id,
                period=date(entry.entry_date.year, entry.entry_date.month, 1),
                amount=signed,
                currency=entry.currency,
                description=line.description or entry.reference,
                cost_center_id=line.cost_center_id,
                journal_entry_line_id=line.id,
            )
        )

    entry.status = JournalEntryStatus.POSTED
    entry.posted_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return entry


def delete_draft_journal_entry(db: Session, entry: JournalEntry) -> None:
    if entry.status != JournalEntryStatus.DRAFT:
        raise JournalEntryError("Only a draft entry can be deleted -- reverse a posted entry instead.")
    db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id == entry.id).delete()
    db.delete(entry)
    db.commit()


def reverse_journal_entry(db: Session, entry: JournalEntry, entry_date: date) -> JournalEntry:
    if entry.status != JournalEntryStatus.POSTED:
        raise JournalEntryError(f"Only a posted entry can be reversed (this one is '{entry.status}').")

    lines = db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id == entry.id).all()
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == entry.company_id).all()}

    reversal = JournalEntry(
        company_id=entry.company_id,
        entry_date=entry_date,
        reference=f"Reversal of {entry.reference}" if entry.reference else "Reversal",
        description=entry.description,
        currency=entry.currency,
        status=JournalEntryStatus.POSTED,
        reverses_entry_id=entry.id,
        posted_at=datetime.utcnow(),
    )
    db.add(reversal)
    db.flush()

    for line in lines:
        new_line = JournalEntryLine(
            journal_entry_id=reversal.id,
            gl_account_id=line.gl_account_id,
            cost_center_id=line.cost_center_id,
            debit_amount=line.credit_amount,
            credit_amount=line.debit_amount,
            description=f"Reversal: {line.description}" if line.description else "Reversal",
        )
        db.add(new_line)
        db.flush()

        account = accounts[line.gl_account_id]
        signed = _signed_amount(account.category, float(new_line.debit_amount), float(new_line.credit_amount))
        db.add(
            ActualLine(
                company_id=entry.company_id,
                gl_account_id=line.gl_account_id,
                period=date(entry_date.year, entry_date.month, 1),
                amount=signed,
                currency=entry.currency,
                description=new_line.description,
                cost_center_id=line.cost_center_id,
                journal_entry_line_id=new_line.id,
            )
        )

    entry.status = JournalEntryStatus.REVERSED
    db.commit()
    db.refresh(reversal)
    return reversal


@dataclass
class TrialBalanceRow:
    gl_account_id: object
    gl_account_code: str
    gl_account_name: str
    category: str
    total_debit: float
    total_credit: float
    net_balance: float


def trial_balance(db: Session, company_id, as_of: date) -> list:
    """Every GL account with at least one posted journal line on or before
    `as_of`, its total debits, total credits, and net balance (signed per
    normal-balance direction). Summing total_debit across every row should
    equal summing total_credit across every row -- that equality, not an
    assumption, is what proves the books actually balance."""
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    entries = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalEntryStatus.POSTED,
            JournalEntry.entry_date <= as_of,
        )
        .all()
    )
    entry_ids = [e.id for e in entries]

    totals: dict = {}
    if entry_ids:
        lines = db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id.in_(entry_ids)).all()
        for line in lines:
            debit, credit = totals.get(line.gl_account_id, (0.0, 0.0))
            totals[line.gl_account_id] = (debit + float(line.debit_amount), credit + float(line.credit_amount))

    rows = []
    for gl_account_id, (debit, credit) in totals.items():
        account = accounts.get(gl_account_id)
        if account is None:
            continue
        rows.append(
            TrialBalanceRow(
                gl_account_id=gl_account_id,
                gl_account_code=account.code,
                gl_account_name=account.name,
                category=account.category,
                total_debit=round(debit, 2),
                total_credit=round(credit, 2),
                net_balance=_signed_amount(account.category, debit, credit),
            )
        )
    return sorted(rows, key=lambda r: r.gl_account_code)
