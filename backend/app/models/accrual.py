import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Accrual(Base):
    """A convenience wrapper around a two-line journal entry (e.g. Dr
    Expense / Cr Accrued Liability, or Dr Accrued Revenue / Cr Revenue),
    posted now for an amount incurred but not yet paid or invoiced, with a
    target date to reverse it -- the standard accrual-then-reverse pattern.
    Nothing here is a new posting mechanism; it just remembers *when* a
    posted journal entry is supposed to be reversed, since the underlying
    reverse_journal_entry() call has no concept of a due date on its own.
    """

    __tablename__ = "accruals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
    reversal_date: Mapped[date] = mapped_column(Date, nullable=False)
    reversed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reversal_journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
