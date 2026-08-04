import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: Optional[uuid.UUID]
    action: str
    actor_email: str
    actor_name: str
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}
