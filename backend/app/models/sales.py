import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SalesActual(Base):
    __tablename__ = "sales_actuals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    period: Mapped[date] = mapped_column(Date, nullable=False)  # first day of the month
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


class SalesForecast(Base):
    __tablename__ = "sales_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    forecast_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    lower_bound: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    upper_bound: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
