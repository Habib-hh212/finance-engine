import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActualLine(Base):
    """Actual spend/revenue posted against a GL account for a period —
    the counterpart to BudgetLine that Cost Controlling compares against."""

    __tablename__ = "actual_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)  # first day of the month
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
