import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_company_access
from app.database import get_db
from app.models import FixedCost
from app.schemas.marginal_costing import FixedCostIn, FixedCostOut, MarginalCostingSummaryOut
from app.services import marginal_costing

router = APIRouter(tags=["marginal-costing"])


@router.post("/fixed-costs", response_model=FixedCostOut)
def create_fixed_cost(payload: FixedCostIn, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    record = FixedCost(company_id=company_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/fixed-costs", response_model=list[FixedCostOut])
def list_fixed_costs(company_id: uuid.UUID = Depends(require_company_access), fiscal_year: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(FixedCost).filter(FixedCost.company_id == company_id)
    if fiscal_year is not None:
        query = query.filter(FixedCost.fiscal_year == fiscal_year)
    return query.all()


@router.get("/marginal-costing/summary", response_model=MarginalCostingSummaryOut)
def get_marginal_costing_summary(fiscal_year: int, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    result = marginal_costing.summary(db, company_id, fiscal_year)
    return MarginalCostingSummaryOut(**result.__dict__)
