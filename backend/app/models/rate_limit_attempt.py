import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RateLimitAttempt(Base):
    """One row per attempt against a rate-limited action -- login, register,
    forgot-password. `key` scopes the window (e.g. "login:user@example.com"
    or "register-ip:203.0.113.4"); app.services.rate_limit counts rows for
    a key within the recent window and deletes ones that have aged out, so
    this table stays small without a separate cleanup job."""

    __tablename__ = "rate_limit_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
