import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_company_access
from app.database import get_db
from app.models import AuditLog
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_log(
    company_id: uuid.UUID = Depends(require_company_access),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)):
    query = db.query(AuditLog).filter(AuditLog.company_id == company_id)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
