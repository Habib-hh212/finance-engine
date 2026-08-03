import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostCenter
from app.schemas.budget import CostCenterCreate, CostCenterOut

router = APIRouter(prefix="/cost-centers", tags=["cost-centers"])


@router.post("", response_model=CostCenterOut)
def create_cost_center(company_id: uuid.UUID, payload: CostCenterCreate, db: Session = Depends(get_db)):
    center = CostCenter(company_id=company_id, **payload.model_dump())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.get("", response_model=list[CostCenterOut])
def list_cost_centers(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(CostCenter).filter(CostCenter.company_id == company_id).all()
