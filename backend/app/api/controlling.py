import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access, require_resource_company_access
from app.database import get_db
from app.models import ActualLine, Budget, User
from app.schemas.actual import ActualLineCreate, ActualLineOut
from app.schemas.variance import BudgetConsumptionOut, CostCenterVarianceRowOut, VarianceRowOut
from app.services import audit, variance

router = APIRouter(tags=["cost-controlling"])


@router.post("/actuals", response_model=ActualLineOut)
def create_actual_line( payload: ActualLineCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    line = ActualLine(company_id=company_id, **payload.model_dump())
    db.add(line)
    db.flush()
    audit.record(db, company_id, "actual_line", line.id, "create", current_user, f"Posted an actual of {line.amount} {line.currency} for {line.period}")
    db.commit()
    db.refresh(line)
    return line


@router.get("/actuals", response_model=list[ActualLineOut])
def list_actual_lines(company_id: uuid.UUID = Depends(require_company_access), gl_account_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    query = db.query(ActualLine).filter(ActualLine.company_id == company_id)
    if gl_account_id is not None:
        query = query.filter(ActualLine.gl_account_id == gl_account_id)
    return query.all()


@router.get("/variance/budget-vs-actual", response_model=list[VarianceRowOut])
def get_budget_vs_actual(company_id: uuid.UUID = Depends(require_company_access), fiscal_year: Optional[int] = Query(None), db: Session = Depends(get_db)):
    rows = variance.budget_vs_actual(db, company_id, fiscal_year=fiscal_year)
    return [VarianceRowOut(**row.__dict__) for row in rows]


@router.get("/variance/budget-consumption/{budget_id}", response_model=BudgetConsumptionOut)
def get_budget_consumption(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    require_resource_company_access(db, current_user, budget.company_id)
    result = variance.budget_consumption(db, budget)
    return BudgetConsumptionOut(**result.__dict__)


@router.get("/variance/cost-center", response_model=list[CostCenterVarianceRowOut])
def get_cost_center_variance(company_id: uuid.UUID = Depends(require_company_access), fiscal_year: Optional[int] = Query(None), db: Session = Depends(get_db)):
    rows = variance.cost_center_variance(db, company_id, fiscal_year=fiscal_year)
    return [CostCenterVarianceRowOut(**row.__dict__) for row in rows]
