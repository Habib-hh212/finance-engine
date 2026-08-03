import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Scenario(Base):
    """A named set of what-if assumptions layered on top of the existing
    Financial Statement Forecast: a flat growth percentage applied to the
    revenue and expense drivers. Not a separate forecasting model -- the
    whole point of Scenario Planning is comparing "what if" against the
    same base case Financial Statement Forecasting already produces.
    """

    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sales_growth_pct: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    expense_growth_pct: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
