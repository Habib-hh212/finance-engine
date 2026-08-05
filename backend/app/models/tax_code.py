import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaxType:
    VAT = "vat"
    GST = "gst"
    OTHER = "other"


class TaxDirection:
    # Tax paid on purchases -- typically recoverable, sits on the debit
    # side as an asset (e.g. "Input VAT").
    INPUT = "input"
    # Tax collected on sales -- owed to the tax authority, sits on the
    # credit side as a liability (e.g. "Output VAT" / "GST Payable").
    OUTPUT = "output"


TAX_TYPES = {TaxType.VAT, TaxType.GST, TaxType.OTHER}
TAX_DIRECTIONS = {TaxDirection.INPUT, TaxDirection.OUTPUT}


class TaxCode(Base):
    """A configurable tax rate, the same way SAP FI handles VAT/GST: rather
    than hard-coding every country's tax law (which changes constantly and
    no small system can keep authoritative), a company sets up one TaxCode
    per rate it actually deals with -- a country, a percentage, whether
    it's input (recoverable, paid on purchases) or output (owed, collected
    on sales), and which G/L account the tax posts to. Applying a tax code
    to a journal line auto-calculates and auto-posts the tax amount; see
    app/services/bookkeeping.py.
    """

    __tablename__ = "tax_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(10), nullable=False)
    rate_pct: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
