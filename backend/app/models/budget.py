import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text
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


# Lines can be added/edited/deleted in these two statuses: while still a
# draft, and after a rejection (so the rejection can actually be acted on
# before resubmitting) -- matches submit_budget, which allows submission
# from either state.
EDITABLE_BUDGET_STATUSES = {BudgetStatus.DRAFT, BudgetStatus.REJECTED}


GL_FORECAST_ROLES = {"cash", "accounts_receivable", "accounts_payable"}


class GLAccount(Base):
    __tablename__ = "gl_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # revenue | expense | asset | liability | equity
    # Which line of the Balance Sheet Forecast this account feeds -- see
    # GL_FORECAST_ROLES. None for accounts with no special forecasting
    # role (carried forward flat in the forecast rather than projected).
    forecast_role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)


# Budget.type mixes "what it covers" (revenue/expense/master) with "how it's
# built and managed" (zero_based/flexible/rolling/capital) in one field
# rather than two orthogonal ones -- a deliberate simplification. A real
# enterprise system might let you cross them (a "flexible expense budget"),
# but nothing here asked for that, and splitting it adds a dimension of
# complexity nobody's using yet.
BUDGET_TYPES = {"revenue", "expense", "master", "zero_based", "flexible", "rolling", "capital"}
DEFAULT_ROLLING_WINDOW_MONTHS = 12


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # see BUDGET_TYPES
    fiscal_year: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=BudgetStatus.DRAFT)
    # Only meaningful when type == "rolling": the fixed size of the forward
    # window, in months. Each roll-forward keeps exactly this many periods.
    rolling_window_months: Mapped[Optional[int]] = mapped_column(nullable=True)


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)  # first day of the month
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # zero_based: required (enforced at submit time) before a line counts as justified.
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # flexible: `amount` above is the FIXED portion; this is the per-unit variable portion.
    # flexed_amount(actual_qty) = amount + variable_rate_per_unit * actual_qty
    variable_rate_per_unit: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    # capital: investment appraisal inputs for this line.
    useful_life_years: Mapped[Optional[int]] = mapped_column(nullable=True)
    annual_cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    # Optional Cost Center Accounting tag -- see ActualLine.cost_center_id.
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id"), nullable=True
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # manager | finance | cfo
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # approved | rejected
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class BudgetVersion(Base):
    """A snapshot of a budget's lines taken every time it's submitted for
    approval. This is what makes "version history" real: reject a budget,
    edit its lines, resubmit, and the prior line values are still visible
    here rather than just overwritten in place.
    """

    __tablename__ = "budget_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    lines_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
