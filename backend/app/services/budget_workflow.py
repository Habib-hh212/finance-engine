"""Sequential budget approval chain: draft -> manager -> finance -> cfo -> approved.

Each submit snapshots the current lines into BudgetVersion, so a
reject -> edit -> resubmit cycle leaves a real trail of what the budget
looked like at each submission, not just the final state.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.budget import (
    APPROVAL_CHAIN,
    ROLE_FOR_STATUS,
    Approval,
    Budget,
    BudgetLine,
    BudgetStatus,
    BudgetVersion,
)


class WorkflowError(ValueError):
    """Raised when a requested transition isn't valid from the budget's current status."""


def _snapshot_lines(line: BudgetLine) -> dict:
    return {
        "gl_account_id": str(line.gl_account_id),
        "period": line.period.isoformat(),
        "amount": float(line.amount),
        "currency": line.currency,
        "justification": line.justification,
        "variable_rate_per_unit": float(line.variable_rate_per_unit) if line.variable_rate_per_unit is not None else None,
        "useful_life_years": line.useful_life_years,
        "annual_cash_flow": float(line.annual_cash_flow) if line.annual_cash_flow is not None else None,
    }


def submit_budget(db: Session, budget: Budget) -> Budget:
    if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REJECTED):
        raise WorkflowError(f"Cannot submit a budget in status '{budget.status}'")

    lines = db.query(BudgetLine).filter(BudgetLine.budget_id == budget.id).all()

    if budget.type == "zero_based":
        if not lines:
            raise WorkflowError("A zero-based budget needs at least one line before it can be submitted")
        unjustified = [line for line in lines if not (line.justification or "").strip()]
        if unjustified:
            raise WorkflowError(
                f"{len(unjustified)} line(s) are missing a justification, required for zero-based budgets"
            )

    version_count = db.query(BudgetVersion).filter(BudgetVersion.budget_id == budget.id).count()
    db.add(
        BudgetVersion(
            budget_id=budget.id,
            version_number=version_count + 1,
            lines_snapshot=[_snapshot_lines(line) for line in lines],
        )
    )

    budget.status = APPROVAL_CHAIN[0]
    db.commit()
    db.refresh(budget)
    return budget


def approve_budget(db: Session, budget: Budget, actor_name: str, comment: str | None = None) -> Budget:
    if budget.status not in APPROVAL_CHAIN:
        raise WorkflowError(f"Budget in status '{budget.status}' is not awaiting approval")

    expected_role = ROLE_FOR_STATUS[budget.status]
    db.add(Approval(budget_id=budget.id, role=expected_role, action="approved", actor_name=actor_name, comment=comment))

    current_index = APPROVAL_CHAIN.index(budget.status)
    if current_index + 1 < len(APPROVAL_CHAIN):
        budget.status = APPROVAL_CHAIN[current_index + 1]
    else:
        budget.status = BudgetStatus.APPROVED

    db.commit()
    db.refresh(budget)
    return budget


def reject_budget(db: Session, budget: Budget, actor_name: str, comment: str | None = None) -> Budget:
    if budget.status not in APPROVAL_CHAIN:
        raise WorkflowError(f"Budget in status '{budget.status}' is not awaiting approval")

    role = ROLE_FOR_STATUS[budget.status]
    db.add(Approval(budget_id=budget.id, role=role, action="rejected", actor_name=actor_name, comment=comment))
    budget.status = BudgetStatus.REJECTED

    db.commit()
    db.refresh(budget)
    return budget


def expected_role(budget: Budget) -> str | None:
    return ROLE_FOR_STATUS.get(budget.status)
