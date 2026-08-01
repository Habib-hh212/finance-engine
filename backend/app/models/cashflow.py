import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

CASH_ITEM_CATEGORIES = {"receivable_collection", "payroll", "vendor_payment", "tax", "loan", "interest", "other"}


class CashItem(Base):
    """A manually entered cash movement not already covered by a sales forecast
    (cash-in) or an approved expense budget (cash-out) — e.g. payroll, a loan
    drawdown, or a one-off tax payment."""

    __tablename__ = "cash_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # in | out
    period: Mapped[date] = mapped_column(Date, nullable=False)  # first day of the month
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
