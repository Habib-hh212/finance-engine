"""Records an audit log entry into the current DB session -- does not
commit; the caller's own commit() (already happening for the entity change
itself) persists it in the same transaction, so an audit row and the change
it describes never diverge (no partial-write where one succeeds and not
the other).
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    company_id: Optional[uuid.UUID],
    entity_type: str,
    entity_id: Optional[uuid.UUID],
    action: str,
    actor: User,
    summary: str,
) -> None:
    db.add(
        AuditLog(
            company_id=company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_email=actor.email,
            actor_name=actor.name,
            summary=summary,
        )
    )
