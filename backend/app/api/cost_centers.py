import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import CostCenter, User
from app.schemas.budget import CostCenterCreate, CostCenterOut
from app.services import audit

router = APIRouter(prefix="/cost-centers", tags=["cost-centers"])


@router.post("", response_model=CostCenterOut)
def create_cost_center( payload: CostCenterCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    center = CostCenter(company_id=company_id, **payload.model_dump())
    db.add(center)
    db.flush()
    audit.record(db, company_id, "cost_center", center.id, "create", current_user, f"Created cost center {center.code} {center.name}")
    db.commit()
    db.refresh(center)
    return center


@router.get("", response_model=list[CostCenterOut])
def list_cost_centers(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(CostCenter).filter(CostCenter.company_id == company_id).all()
