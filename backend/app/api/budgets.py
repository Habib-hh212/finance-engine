import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access, require_resource_company_access
from app.database import get_db
from app.models import Approval, Budget, BudgetLine, BudgetVersion, GLAccount, User
from app.models.budget import DEFAULT_ROLLING_WINDOW_MONTHS, EDITABLE_BUDGET_STATUSES
from app.schemas.budget import (
    ApprovalAction,
    BudgetCreate,
    BudgetDetail,
    BudgetLineIn,
    BudgetLineOut,
    BudgetLineUpdate,
    BudgetOut,
    BudgetVersionOut,
    GLAccountCreate,
    GLAccountOut,
    GLAccountUpdate,
)
from app.schemas.variance import CapitalAppraisalRowOut, FlexibleVarianceRowOut
from app.services import audit, budget_workflow, capital_budget, rolling_budget, variance

router = APIRouter(tags=["budgets"])


@router.post("/gl-accounts", response_model=GLAccountOut)
def create_gl_account( payload: GLAccountCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    account = GLAccount(company_id=company_id, **payload.model_dump())
    db.add(account)
    db.flush()
    audit.record(db, company_id, "gl_account", account.id, "create", current_user, f"Created GL account {account.code} {account.name}")
    db.commit()
    db.refresh(account)
    return account


@router.get("/gl-accounts", response_model=list[GLAccountOut])
def list_gl_accounts(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(GLAccount).filter(GLAccount.company_id == company_id).all()


@router.patch("/gl-accounts/{account_id}", response_model=GLAccountOut)
def update_gl_account(
    account_id: uuid.UUID,
    payload: GLAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = db.get(GLAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="GL account not found")
    require_resource_company_access(db, current_user, account.company_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(account, field, value)
    audit.record(
        db,
        account.company_id,
        "gl_account",
        account.id,
        "update",
        current_user,
        f"Updated GL account {account.code} {account.name} ({', '.join(changes.keys()) or 'no changes'})",
    )
    db.commit()
    db.refresh(account)
    return account


@router.post("/budgets", response_model=BudgetOut)
def create_budget( payload: BudgetCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    data = payload.model_dump()
    if data["type"] == "rolling" and data["rolling_window_months"] is None:
        data["rolling_window_months"] = DEFAULT_ROLLING_WINDOW_MONTHS
    budget = Budget(company_id=company_id, **data)
    db.add(budget)
    db.flush()
    audit.record(
        db, company_id, "budget", budget.id, "create", current_user, f"Created {data['type']} budget '{budget.name}' (FY{budget.fiscal_year})"
    )
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(Budget).filter(Budget.company_id == company_id).all()


def _get_budget_or_404(db: Session, budget_id: uuid.UUID, current_user: User) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    require_resource_company_access(db, current_user, budget.company_id)
    return budget


@router.get("/budgets/{budget_id}", response_model=BudgetDetail)
def get_budget(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = _get_budget_or_404(db, budget_id, current_user)
    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget_id).all()
    approvals = db.query(Approval).filter(Approval.budget_id == budget_id).order_by(Approval.acted_at).all()
    return BudgetDetail(
        **BudgetOut.model_validate(budget).model_dump(),
        lines=[BudgetLineOut.model_validate(line) for line in lines],
        approvals=approvals,
    )


@router.post("/budgets/{budget_id}/lines", response_model=list[BudgetLineOut])
def add_budget_lines(
    budget_id: uuid.UUID,
    lines: list[BudgetLineIn],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = _get_budget_or_404(db, budget_id, current_user)
    if budget.status not in EDITABLE_BUDGET_STATUSES:
        raise HTTPException(status_code=409, detail="Budget lines can only be edited while status is 'draft' or 'rejected'")

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
            cost_center_id=line.cost_center_id,
        )
        db.add(record)
        created.append(record)
    audit.record(
        db, budget.company_id, "budget", budget.id, "update", current_user, f"Added {len(created)} line(s) to budget '{budget.name}'"
    )
    db.commit()
    for record in created:
        db.refresh(record)
    return created


def _get_line_or_404(db: Session, budget_id: uuid.UUID, line_id: uuid.UUID) -> BudgetLine:
    line = db.query(BudgetLine).filter(BudgetLine.id == line_id, BudgetLine.budget_id == budget_id).first()
    if line is None:
        raise HTTPException(status_code=404, detail="Budget line not found")
    return line


@router.patch("/budgets/{budget_id}/lines/{line_id}", response_model=BudgetLineOut)
def update_budget_line(
    budget_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: BudgetLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = _get_budget_or_404(db, budget_id, current_user)
    if budget.status not in EDITABLE_BUDGET_STATUSES:
        raise HTTPException(status_code=409, detail="Budget lines can only be edited while status is 'draft' or 'rejected'")
    line = _get_line_or_404(db, budget_id, line_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(line, field, value)
    audit.record(db, budget.company_id, "budget_line", line.id, "update", current_user, f"Edited a line on budget '{budget.name}'")
    db.commit()
    db.refresh(line)
    return line


@router.delete("/budgets/{budget_id}/lines/{line_id}", status_code=204)
def delete_budget_line(
    budget_id: uuid.UUID, line_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    budget = _get_budget_or_404(db, budget_id, current_user)
    if budget.status not in EDITABLE_BUDGET_STATUSES:
        raise HTTPException(status_code=409, detail="Budget lines can only be edited while status is 'draft' or 'rejected'")
    line = _get_line_or_404(db, budget_id, line_id)
    audit.record(db, budget.company_id, "budget_line", line.id, "delete", current_user, f"Deleted a line from budget '{budget.name}'")
    db.delete(line)
    db.commit()


@router.post("/budgets/{budget_id}/submit", response_model=BudgetOut)
def submit_budget(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = _get_budget_or_404(db, budget_id, current_user)
    try:
        result = budget_workflow.submit_budget(db, budget)
        audit.record(db, budget.company_id, "budget", budget.id, "submit", current_user, f"Submitted budget '{budget.name}' for approval")
        db.commit()
        db.refresh(result)
        return result
    except budget_workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/budgets/{budget_id}/approve", response_model=BudgetOut)
def approve_budget(
    budget_id: uuid.UUID, payload: ApprovalAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    budget = _get_budget_or_404(db, budget_id, current_user)
    role = budget_workflow.expected_role(budget)
    try:
        result = budget_workflow.approve_budget(db, budget, payload.actor_name, payload.comment)
        audit.record(
            db, budget.company_id, "budget", budget.id, "approve", current_user, f"Approved budget '{budget.name}' as {role} ({payload.actor_name})"
        )
        db.commit()
        db.refresh(result)
        return result
    except budget_workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/budgets/{budget_id}/reject", response_model=BudgetOut)
def reject_budget(
    budget_id: uuid.UUID, payload: ApprovalAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    budget = _get_budget_or_404(db, budget_id, current_user)
    role = budget_workflow.expected_role(budget)
    try:
        result = budget_workflow.reject_budget(db, budget, payload.actor_name, payload.comment)
        audit.record(
            db, budget.company_id, "budget", budget.id, "reject", current_user, f"Rejected budget '{budget.name}' as {role} ({payload.actor_name})"
        )
        db.commit()
        db.refresh(result)
        return result
    except budget_workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/budgets/{budget_id}/versions", response_model=list[BudgetVersionOut])
def list_budget_versions(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _get_budget_or_404(db, budget_id, current_user)
    return (
        db.query(BudgetVersion)
        .filter(BudgetVersion.budget_id == budget_id)
        .order_by(BudgetVersion.version_number)
        .all()
    )


@router.post("/budgets/{budget_id}/roll-forward", response_model=BudgetOut)
def roll_forward_budget(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = _get_budget_or_404(db, budget_id, current_user)
    try:
        return rolling_budget.roll_forward(db, budget)
    except rolling_budget.RollForwardError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/budgets/{budget_id}/flexible-variance", response_model=list[FlexibleVarianceRowOut])
def get_flexible_variance(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = _get_budget_or_404(db, budget_id, current_user)
    if budget.type != "flexible":
        raise HTTPException(status_code=409, detail="Flexible variance only applies to 'flexible' budgets")
    rows = variance.flexible_budget_variance(db, budget)
    return [FlexibleVarianceRowOut(**row.__dict__) for row in rows]


@router.get("/budgets/{budget_id}/capital-appraisal", response_model=list[CapitalAppraisalRowOut])
def get_capital_appraisal(budget_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = _get_budget_or_404(db, budget_id, current_user)
    if budget.type != "capital":
        raise HTTPException(status_code=409, detail="Capital appraisal only applies to 'capital' budgets")
    rows = capital_budget.capital_appraisal(db, budget)
    return [CapitalAppraisalRowOut(**row.__dict__) for row in rows]
