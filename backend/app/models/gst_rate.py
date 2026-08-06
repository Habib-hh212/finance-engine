import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GstRate(Base):
    """A combined India GST rate (e.g. 18%) with three separate G/L
    accounts for its components -- CGST + SGST post together for an
    intra-state transaction, IGST posts alone for an inter-state one,
    decided at posting time by comparing the transaction's place of supply
    (the customer's or vendor's state) against the company's home_state.
    Real GST ledgers are kept separate this way (Output CGST Payable,
    Output SGST Payable, Output IGST Payable, and the input/ITC
    equivalents), so a single flat-rate G/L account like TaxCode uses
    isn't enough here."""

    __tablename__ = "gst_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # input | output
    cgst_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    sgst_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    igst_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


GST_DIRECTIONS = {"input", "output"}
