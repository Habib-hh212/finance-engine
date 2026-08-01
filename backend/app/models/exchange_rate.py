import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExchangeRate(Base):
    """Daily rate to convert 1 unit of from_currency into to_currency."""

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("from_currency", "to_currency", "rate_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
