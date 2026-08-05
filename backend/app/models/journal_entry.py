import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JournalEntryStatus:
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class JournalEntry(Base):
    """A double-entry bookkeeping document -- what SAP FI calls a journal
    entry (an "FI document"). Its lines must balance (total debits == total
    credits) before it can be posted; enforcing that is the entire reason
    this module exists, since nothing else in this system requires it --
    the existing `ActualLine` posting on the Controlling page is a single
    unbalanced amount against one account, not a real bookkeeping entry.
    """

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=JournalEntryStatus.DRAFT)
    # Set only on a reversing entry -- points back at the entry it reverses.
    # A posted entry is never edited or deleted, only reversed with a new
    # offsetting entry -- the real accounting principle: the books always
    # show what actually happened, including the correction.
    reverses_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class JournalEntryLine(Base):
    """One debit or credit line within a journal entry. Exactly one of
    debit_amount/credit_amount is nonzero -- a line is either a debit line
    or a credit line, never both, the same way a real FI line item works."""

    __tablename__ = "journal_entry_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("cost_centers.id"), nullable=True)
    debit_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    credit_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Set only on an auto-generated tax line (see app/services/bookkeeping.py
    # apply_tax_code) -- never on the net line it was calculated from. This
    # is what a VAT/GST return sums: the actual tax G/L postings, the same
    # way SAP FI derives a tax return from the tax account's activity.
    tax_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tax_codes.id"), nullable=True)
    tax_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
