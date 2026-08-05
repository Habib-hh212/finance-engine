import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import Accrual, GLAccount, JournalEntry, JournalEntryLine, User
from app.schemas.accrual import AccrualCreate, AccrualOut
from app.services import accruals, audit

router = APIRouter(tags=["accruals"])


def _accrual_out(db: Session, accrual: Accrual) -> AccrualOut:
    entry = db.get(JournalEntry, accrual.journal_entry_id)
    lines = db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id == entry.id).all()
    debit_line = next(line for line in lines if float(line.debit_amount) > 0)
    credit_line = next(line for line in lines if float(line.credit_amount) > 0)
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == accrual.company_id).all()}
    return AccrualOut(
        id=accrual.id,
        journal_entry_id=entry.id,
        entry_date=entry.entry_date,
        reference=entry.reference,
        description=entry.description,
        amount=float(debit_line.debit_amount),
        debit_gl_account_id=debit_line.gl_account_id,
        debit_gl_account_code=accounts[debit_line.gl_account_id].code if debit_line.gl_account_id in accounts else "?",
        credit_gl_account_id=credit_line.gl_account_id,
        credit_gl_account_code=accounts[credit_line.gl_account_id].code if credit_line.gl_account_id in accounts else "?",
        reversal_date=accrual.reversal_date,
        reversed=accrual.reversed,
        reversal_journal_entry_id=accrual.reversal_journal_entry_id,
        due_for_reversal=(not accrual.reversed) and accrual.reversal_date <= date.today(),
    )


@router.post("/accruals", response_model=AccrualOut)
def create_accrual(payload: AccrualCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        accrual = accruals.create_accrual(db, company_id, **payload.model_dump())
    except accruals.AccrualError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "accrual", accrual.id, "create", current_user, f"Created accrual of {payload.amount} due {payload.reversal_date}")
    db.commit()
    return _accrual_out(db, accrual)


@router.get("/accruals", response_model=list[AccrualOut])
def list_accruals(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    rows = db.query(Accrual).filter(Accrual.company_id == company_id).all()
    out = [_accrual_out(db, a) for a in rows]
    return sorted(out, key=lambda a: a.entry_date, reverse=True)


@router.post("/accruals/{accrual_id}/reverse", response_model=AccrualOut)
def reverse_accrual(accrual_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accrual = db.get(Accrual, accrual_id)
    if accrual is None or accrual.company_id != company_id:
        raise HTTPException(status_code=404, detail="Accrual not found")
    try:
        accrual = accruals.reverse_accrual(db, accrual)
    except accruals.AccrualError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(db, company_id, "accrual", accrual.id, "reverse", current_user, "Reversed an accrual")
    db.commit()
    return _accrual_out(db, accrual)
