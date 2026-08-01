"""Sequential budget approval chain: draft -> manager -> finance -> cfo -> approved.

Phase 1 keeps this linear and un-versioned (one active state per budget).
Version history / branching workflows are a Phase 2 item.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.budget import APPROVAL_CHAIN, ROLE_FOR_STATUS, Approval, Budget, BudgetStatus


class WorkflowError(ValueError):
    """Raised when a requested transition isn't valid from the budget's current status."""


def submit_budget(db: Session, budget: Budget) -> Budget:
    if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REJECTED):
        raise WorkflowError(f"Cannot submit a budget in status '{budget.status}'")
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
