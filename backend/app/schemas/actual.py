import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class ActualLineCreate(BaseModel):
    gl_account_id: uuid.UUID
    period: date
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    actual_quantity: Optional[float] = None
    cost_center_id: Optional[uuid.UUID] = None


class ActualLineOut(BaseModel):
    id: uuid.UUID
    gl_account_id: uuid.UUID
    period: date
    amount: float
    currency: str
    description: Optional[str]
    actual_quantity: Optional[float] = None
    cost_center_id: Optional[uuid.UUID] = None
    journal_entry_line_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
