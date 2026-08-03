import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FixedCost(Base):
    """A period (not per-unit) cost -- rent, salaried staff, depreciation,
    insurance -- that doesn't vary with production/sales volume. Marginal
    costing keeps these separate from Product.unit_variable_cost by design:
    lumping them per-unit is exactly the distortion CVP analysis exists to
    avoid.
    """

    __tablename__ = "fixed_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
