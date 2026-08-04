import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    """Who changed what, when -- one row per mutating action on an entity
    that matters for financial integrity (budgets through their approval
    chain, actuals, GL accounts, cost centers, scenarios). Deliberately a
    flat human-readable `summary` per event rather than a structured
    before/after diff -- for the entities this covers, "Approved budget
    'Marketing Budget' (finance)" is more immediately useful to read than a
    JSON field-by-field delta, and it's honest about not attempting a
    generic diff engine.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable because not every audited entity belongs to a company --
    # exchange rates are global (see fx.py), so their audit rows carry no
    # company_id rather than being attributed to whichever company happened
    # to trigger the change.
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
