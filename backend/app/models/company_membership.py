import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanyMembership(Base):
    """Which users can access which companies. Every endpoint that takes a
    company_id is expected to be gated by app.auth.require_company_access,
    which checks for a row here -- without it, any logged-in user could
    read or write any company's data just by knowing (or guessing) its id,
    since login alone was the only real gate before this."""

    __tablename__ = "company_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
