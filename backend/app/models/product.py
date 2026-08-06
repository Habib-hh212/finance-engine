import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Variable cost to produce/deliver one unit — needed for contribution-margin
    # analysis. Nullable: not every product has this set, in which case
    # profitability figures for it are omitted rather than assumed zero.
    unit_variable_cost: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    # India GST place-of-supply: compared against Company.home_state to
    # decide CGST+SGST (same state) vs IGST (different state) on a sale.
    # A populated gstin also marks this customer as a B2B (registered)
    # counterparty for GSTR-1 reporting -- blank means B2C.
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
