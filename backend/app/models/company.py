import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # This company's own registered state -- the anchor place-of-supply
    # comparison point for India GST: a sale/purchase is intra-state (CGST +
    # SGST) when the counterparty's state matches this, inter-state (IGST)
    # otherwise. Blank for companies that don't deal in Indian GST.
    home_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
