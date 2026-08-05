"""Month-end and year-end close.

`period_close_status` is a read-only checklist -- it doesn't change
anything, it just answers "is this period ready to close" by querying
what's already in the ledger and the fixed-assets sub-ledger.

`close_fiscal_year` posts the one thing an accounting period genuinely
needs at year-end that nothing else here does automatically: zeroing
every revenue and expense account's net activity for the year into
Retained Earnings, via a single balanced closing journal entry. Balance
sheet accounts (asset/liability/equity) need no such step -- the Trial
Balance and GL Ledger already sum a company's *entire* posted history, so
their balances carry forward into next year automatically, by
construction. Closing revenue and expense is the only carry-forward
mechanic a real double-entry ledger needs.
"""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import Accrual, Asset, DepreciationEntry, GLAccount, JournalEntry
from app.models.fixed_asset import AssetStatus
from app.models.journal_entry import JournalEntryStatus
from app.services import bookkeeping
from app.services.financial_statements import income_statement


class PeriodCloseError(ValueError):
    """Raised when a year-end close can't proceed."""


@dataclass
class AssetDepreciationGap:
    asset_id: object
    code: str


@dataclass
class PeriodCloseStatus:
    period: date
    trial_balance_is_balanced: bool
    draft_entries_count: int
    depreciation_run_done: bool
    assets_missing_depreciation: list
    accruals_due_for_reversal: int


def period_close_status(db: Session, company_id, period: date) -> PeriodCloseStatus:
    period = date(period.year, period.month, 1)
    period_end = date(period.year, period.month, monthrange(period.year, period.month)[1])

    tb_rows = bookkeeping.trial_balance(db, company_id, period_end)
    total_debit = round(sum(r.total_debit for r in tb_rows), 2)
    total_credit = round(sum(r.total_credit for r in tb_rows), 2)

    draft_count = (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == company_id, JournalEntry.status == JournalEntryStatus.DRAFT, JournalEntry.entry_date <= period_end)
        .count()
    )

    depreciated_asset_ids = {
        row.asset_id
        for row in db.query(DepreciationEntry)
        .join(Asset, Asset.id == DepreciationEntry.asset_id)
        .filter(Asset.company_id == company_id, DepreciationEntry.period == period)
        .all()
    }
    active_assets = (
        db.query(Asset)
        .filter(Asset.company_id == company_id, Asset.status == AssetStatus.ACTIVE, Asset.acquisition_date <= period_end)
        .order_by(Asset.code)
        .all()
    )
    missing = [AssetDepreciationGap(asset_id=a.id, code=a.code) for a in active_assets if a.id not in depreciated_asset_ids]

    accruals_due = (
        db.query(Accrual)
        .filter(Accrual.company_id == company_id, Accrual.reversed.is_(False), Accrual.reversal_date <= period_end)
        .count()
    )

    return PeriodCloseStatus(
        period=period,
        trial_balance_is_balanced=abs(total_debit - total_credit) <= 0.01,
        draft_entries_count=draft_count,
        depreciation_run_done=len(depreciated_asset_ids) > 0,
        assets_missing_depreciation=missing,
        accruals_due_for_reversal=accruals_due,
    )


def close_fiscal_year(db: Session, company_id, start: date, end: date, retained_earnings_gl_account_id) -> tuple:
    account = db.get(GLAccount, retained_earnings_gl_account_id)
    if account is None or account.company_id != company_id:
        raise PeriodCloseError("Retained earnings account doesn't belong to this company.")
    if account.category != "equity":
        raise PeriodCloseError("Retained earnings account must be an equity account.")

    stmt = income_statement(db, company_id, start, end)
    lines = []
    retained_earnings_effect = 0.0

    for line in stmt.revenue_lines:
        if line.amount > 0:
            lines.append(bookkeeping.LineInput(gl_account_id=line.gl_account_id, debit_amount=line.amount, description=f"Close {line.code}"))
        elif line.amount < 0:
            lines.append(bookkeeping.LineInput(gl_account_id=line.gl_account_id, credit_amount=abs(line.amount), description=f"Close {line.code}"))
        retained_earnings_effect += line.amount

    for line in stmt.expense_lines:
        if line.amount > 0:
            lines.append(bookkeeping.LineInput(gl_account_id=line.gl_account_id, credit_amount=line.amount, description=f"Close {line.code}"))
        elif line.amount < 0:
            lines.append(bookkeeping.LineInput(gl_account_id=line.gl_account_id, debit_amount=abs(line.amount), description=f"Close {line.code}"))
        retained_earnings_effect -= line.amount

    if not lines:
        raise PeriodCloseError("Nothing to close -- no revenue or expense activity in this period.")

    retained_earnings_effect = round(retained_earnings_effect, 2)
    if retained_earnings_effect > 0:
        lines.append(bookkeeping.LineInput(gl_account_id=retained_earnings_gl_account_id, credit_amount=retained_earnings_effect))
    elif retained_earnings_effect < 0:
        lines.append(bookkeeping.LineInput(gl_account_id=retained_earnings_gl_account_id, debit_amount=abs(retained_earnings_effect)))

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        end,
        lines,
        reference=f"Year-end close FY{end.year}",
        description=f"Closed revenue and expense for {start.isoformat()} to {end.isoformat()} to retained earnings",
        currency="USD",
    )
    lines_count = len(lines)
    entry = bookkeeping.post_journal_entry(db, entry)
    return entry, stmt.net_profit, lines_count
