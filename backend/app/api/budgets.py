import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Approval, Budget, BudgetLine, GLAccount
from app.models.budget import DEFAULT_ROLLING_WINDOW_MONTHS
from app.schemas.budget import (
    ApprovalAction,
    BudgetCreate,
    BudgetDetail,
    BudgetLineIn,
    BudgetLineOut,
    BudgetOut,
    GLAccountCreate,
    GLAccountOut,
)
from app.schemas.variance import CapitalAppraisalRowOut, FlexibleVarianceRowOut
from app.services import budget_workflow, capital_budget, rolling_budget, variance

router = APIRouter(tags=["budgets"])


@router.post("/gl-accounts", response_model=GLAccountOut)
def create_gl_account(company_id: uuid.UUID, payload: GLAccountCreate, db: Session = Depends(get_db)):
    account = GLAccount(company_id=company_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/gl-accounts", response_model=list[GLAccountOut])
def list_gl_accounts(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(GLAccount).filter(GLAccount.company_id == company_id).all()


@router.post("/budgets", response_model=BudgetOut)
def create_budget(company_id: uuid.UUID, payload: BudgetCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data["type"] == "rolling" and data["rolling_window_months"] is None:
        data["rolling_window_months"] = DEFAULT_ROLLING_WINDOW_MONTHS
    budget = Budget(company_id=company_id, **data)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(Budget).filter(Budget.company_id == company_id).all()


def _get_budget_or_404(db: Session, budget_id: uuid.UUID) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.get("/budgets/{budget_id}", response_model=BudgetDetail)
def get_budget(budget_id: uuid.UUID, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget_id).all()
    approvals = db.query(Approval).filter(Approval.budget_id == budget_id).order_by(Approval.acted_at).all()
    return BudgetDetail(
        **BudgetOut.model_validate(budget).model_dump(),
        lines=[BudgetLineOut.model_validate(line) for line in lines],
        approvals=approvals,
    )


@router.post("/budgets/{budget_id}/lines", response_model=list[BudgetLineOut])
def add_budget_lines(budget_id: uuid.UUID, lines: list[BudgetLineIn], db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    if budget.status != "draft":
        raise HTTPException(status_code=409, detail="Budget lines can only be edited while status is 'draft'")

    created = []
    for line in lines:
        record = BudgetLine(
            budget_id=budget_id,
            gl_account_id=line.gl_account_id,
            period=line.period,
            amount=line.amount,
            currency=line.currency or budget.currency,
            justification=line.justification,
            variable_rate_per_unit=line.variable_rate_per_unit,
            useful_life_years=line.useful_life_years,
            annual_cash_flow=line.annual_cash_flow,
        )
        db.add(record)
        created.append(record)
    db.commit()
    for record in created:
        db.refresh(record)
    return created


@router.post("/budgets/{budget_id}/submit", response_model=BudgetOut)
def submit_budget(budget_id: uuid.UUID, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    try:
        return budget_workflow.submit_budget(db, budget)
    except budget_workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/budgets/{budget_id}/approve", response_model=BudgetOut)
def approve_budget(budget_id: uuid.UUID, payload: ApprovalAction, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    try:
        return budget_workflow.approve_budget(db, budget, payload.actor_name, payload.comment)
    except budget_workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/budgets/{budget_id}/reject", response_model=BudgetOut)
def reject_budget(budget_id: uuid.UUID, payload: ApprovalAction, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    try:
        return budget_workflow.reject_budget(db, budget, payload.actor_name, payload.comment)
    except budget_workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/budgets/{budget_id}/roll-forward", response_model=BudgetOut)
def roll_forward_budget(budget_id: uuid.UUID, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    try:
        return rolling_budget.roll_forward(db, budget)
    except rolling_budget.RollForwardError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/budgets/{budget_id}/flexible-variance", response_model=list[FlexibleVarianceRowOut])
def get_flexible_variance(budget_id: uuid.UUID, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    if budget.type != "flexible":
        raise HTTPException(status_code=409, detail="Flexible variance only applies to 'flexible' budgets")
    rows = variance.flexible_budget_variance(db, budget)
    return [FlexibleVarianceRowOut(**row.__dict__) for row in rows]


@router.get("/budgets/{budget_id}/capital-appraisal", response_model=list[CapitalAppraisalRowOut])
def get_capital_appraisal(budget_id: uuid.UUID, db: Session = Depends(get_db)):
    budget = _get_budget_or_404(db, budget_id)
    if budget.type != "capital":
        raise HTTPException(status_code=409, detail="Capital appraisal only applies to 'capital' budgets")
    rows = capital_budget.capital_appraisal(db, budget)
    return [CapitalAppraisalRowOut(**row.__dict__) for row in rows]
