import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DepreciationMethod:
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    SUM_OF_YEARS_DIGITS = "sum_of_years_digits"


DEPRECIATION_METHODS = {
    DepreciationMethod.STRAIGHT_LINE,
    DepreciationMethod.DECLINING_BALANCE,
    DepreciationMethod.SUM_OF_YEARS_DIGITS,
}


class AssetStatus:
    ACTIVE = "active"
    SOLD = "sold"
    SCRAPPED = "scrapped"
    LOST = "lost"


ASSET_STATUSES = {AssetStatus.ACTIVE, AssetStatus.SOLD, AssetStatus.SCRAPPED, AssetStatus.LOST}
DISPOSED_STATUSES = {AssetStatus.SOLD, AssetStatus.SCRAPPED, AssetStatus.LOST}


class AssetClass(Base):
    """SAP FI-AA calls this "account determination" -- rather than picking
    G/L accounts on every single asset transaction, a company sets up one
    class per kind of asset it owns (e.g. "IT Equipment", "Vehicles") with
    the five accounts every transaction on an asset in that class needs:
    where its cost sits, where depreciation expenses to, where accumulated
    depreciation (the contra-asset) sits, and where a disposal's gain or
    loss lands. Also carries the default depreciation policy new assets in
    this class are pre-filled with.
    """

    __tablename__ = "asset_classes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    apc_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    depreciation_expense_gl_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False
    )
    accumulated_depreciation_gl_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False
    )
    disposal_gain_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    disposal_loss_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    default_depreciation_method: Mapped[str] = mapped_column(String(30), nullable=False, default=DepreciationMethod.STRAIGHT_LINE)
    default_useful_life_years: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=5)
    default_declining_balance_factor: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=2.0)


class Asset(Base):
    """One capitalized fixed asset. `capitalized_cost` (SAP calls this
    "APC" -- Acquisition and Production Cost) minus accumulated
    depreciation (summed from DepreciationEntry) is the net book value at
    any point in time -- never stored directly, always derived, so it can
    never drift out of sync with the depreciation history."""

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    asset_class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("asset_classes.id"), nullable=False)
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("cost_centers.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    capitalized_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    salvage_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    useful_life_years: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    depreciation_method: Mapped[str] = mapped_column(String(30), nullable=False)
    declining_balance_factor: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=2.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssetStatus.ACTIVE)
    disposal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    disposal_proceeds: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    disposal_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acquisition_journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )


class DepreciationEntry(Base):
    """One posted period of depreciation for one asset -- the running
    history that both proves accumulated depreciation and stops the same
    asset+period from ever being depreciated twice."""

    __tablename__ = "depreciation_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    depreciation_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    accumulated_depreciation_after: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    net_book_value_after: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
