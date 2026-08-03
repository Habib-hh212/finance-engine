import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Sequential approval chain: draft -> submitted -> manager -> finance -> cfo -> approved (locked).
# Phase 1 keeps this as a single linear chain per budget, not versioned workflow (that's Phase 2).
APPROVAL_CHAIN = ["pending_manager", "pending_finance", "pending_cfo"]
ROLE_FOR_STATUS = {"pending_manager": "manager", "pending_finance": "finance", "pending_cfo": "cfo"}


class BudgetStatus:
    DRAFT = "draft"
    PENDING_MANAGER = "pending_manager"
    PENDING_FINANCE = "pending_finance"
    PENDING_CFO = "pending_cfo"
    APPROVED = "approved"
    REJECTED = "rejected"


class GLAccount(Base):
    __tablename__ = "gl_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # revenue | expense | asset | liability | equity


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # revenue | expense | master
    fiscal_year: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=BudgetStatus.DRAFT)


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)  # first day of the month
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # manager | finance | cfo
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # approved | rejected
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
