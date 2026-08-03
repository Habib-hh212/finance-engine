import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StandardCost(Base):
    """The standard (expected) cost sheet for one unit of a product --
    material, labor, and overhead components. One row per product; a new
    POST to the same product_id updates it in place rather than creating a
    parallel version, since this represents "the current standard," not a
    history of standards.
    """

    __tablename__ = "standard_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    material_std_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    material_std_qty: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    labor_std_rate: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    labor_std_hours: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    variable_overhead_std_rate: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    fixed_overhead_std_rate: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    # Total fixed overhead budgeted for the period this standard applies to --
    # needed to compute the fixed-overhead budget and volume variances.
    fixed_overhead_budgeted: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)


class ProductionActual(Base):
    """What actually happened in production for one product in one period --
    the counterpart StandardCost is compared against."""

    __tablename__ = "production_actuals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)  # first day of the month

    units_produced: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    material_actual_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    material_actual_qty: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    labor_actual_rate: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    labor_actual_hours: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    actual_variable_overhead: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    actual_fixed_overhead: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
