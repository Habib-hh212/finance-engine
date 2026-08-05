import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchType:
    AUTO = "auto"
    MANUAL = "manual"


class BankStatementLine(Base):
    """One transaction from an uploaded bank statement. `amount` follows
    the bank's own sign convention -- positive for money in (a deposit,
    interest credited), negative for money out (a withdrawal, a fee).

    Matches against `ActualLine`, not `JournalEntryLine`, deliberately:
    every posted journal line already generates exactly one ActualLine
    with the correct signed amount (positive = cash increased, for a
    debit-normal cash account), so it lines up with the bank's own sign
    convention with no per-account category logic needed here. It's also
    the same ledger every other report in this app (Cash Flow Statement,
    Balance Sheet, Income Statement) already reads from, and it naturally
    includes a manual "quick actuals post" against a cash account, not
    just journal-entry-sourced postings. See
    app/services/bank_reconciliation.py for the matching algorithm and
    the reconciliation proof.
    """

    __tablename__ = "bank_statement_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    cash_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    matched_actual_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("actual_lines.id"), nullable=True)
    match_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
