import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActualLine, Budget
from app.schemas.actual import ActualLineCreate, ActualLineOut
from app.schemas.variance import BudgetConsumptionOut, VarianceRowOut
from app.services import variance

router = APIRouter(tags=["cost-controlling"])


@router.post("/actuals", response_model=ActualLineOut)
def create_actual_line(company_id: uuid.UUID, payload: ActualLineCreate, db: Session = Depends(get_db)):
    line = ActualLine(company_id=company_id, **payload.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.get("/actuals", response_model=list[ActualLineOut])
def list_actual_lines(company_id: uuid.UUID, gl_account_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    query = db.query(ActualLine).filter(ActualLine.company_id == company_id)
    if gl_account_id is not None:
        query = query.filter(ActualLine.gl_account_id == gl_account_id)
    return query.all()


@router.get("/variance/budget-vs-actual", response_model=list[VarianceRowOut])
def get_budget_vs_actual(company_id: uuid.UUID, fiscal_year: Optional[int] = Query(None), db: Session = Depends(get_db)):
    rows = variance.budget_vs_actual(db, company_id, fiscal_year=fiscal_year)
    return [VarianceRowOut(**row.__dict__) for row in rows]


@router.get("/variance/budget-consumption/{budget_id}", response_model=BudgetConsumptionOut)
def get_budget_consumption(budget_id: uuid.UUID, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    result = variance.budget_consumption(db, budget)
    return BudgetConsumptionOut(**result.__dict__)
