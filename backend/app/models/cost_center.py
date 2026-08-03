import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CostCenter(Base):
    """A responsibility unit (department, team, plant) that actuals and
    budget lines can optionally be tagged against, independent of GL
    account -- SAP CO's Cost Center Accounting. Tagging is optional on both
    ActualLine and BudgetLine so existing untagged data keeps working."""

    __tablename__ = "cost_centers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
