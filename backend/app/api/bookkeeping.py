import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import GLAccount, JournalEntry, JournalEntryLine, User
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryLineOut,
    JournalEntryOut,
    ReverseJournalEntryIn,
    TrialBalanceOut,
    TrialBalanceRowOut,
)
from app.services import audit, bookkeeping

router = APIRouter(tags=["bookkeeping"])


def _line_inputs(payload_lines) -> list[bookkeeping.LineInput]:
    return [
        bookkeeping.LineInput(
            gl_account_id=line.gl_account_id,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            cost_center_id=line.cost_center_id,
            description=line.description,
        )
        for line in payload_lines
    ]


def _entry_out(db: Session, entry: JournalEntry) -> JournalEntryOut:
    lines = db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id == entry.id).all()
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == entry.company_id).all()}
    line_outs = [
        JournalEntryLineOut(
            id=line.id,
            gl_account_id=line.gl_account_id,
            gl_account_code=accounts[line.gl_account_id].code if line.gl_account_id in accounts else "?",
            gl_account_name=accounts[line.gl_account_id].name if line.gl_account_id in accounts else "?",
            cost_center_id=line.cost_center_id,
            debit_amount=float(line.debit_amount),
            credit_amount=float(line.credit_amount),
            description=line.description,
        )
        for line in lines
    ]
    return JournalEntryOut(
        id=entry.id,
        entry_date=entry.entry_date,
        reference=entry.reference,
        description=entry.description,
        currency=entry.currency,
        status=entry.status,
        reverses_entry_id=entry.reverses_entry_id,
        created_at=entry.created_at,
        posted_at=entry.posted_at,
        lines=line_outs,
    )


def _get_entry_or_404(db: Session, entry_id: uuid.UUID) -> JournalEntry:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@router.post("/journal-entries", response_model=JournalEntryOut)
def create_journal_entry(
    company_id: uuid.UUID, payload: JournalEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        entry = bookkeeping.create_journal_entry(
            db,
            company_id,
            payload.entry_date,
            _line_inputs(payload.lines),
            reference=payload.reference,
            description=payload.description,
            currency=payload.currency,
        )
    except bookkeeping.JournalEntryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(
        db, company_id, "journal_entry", entry.id, "create", current_user, f"Created draft journal entry {entry.reference or entry.id}"
    )
    db.commit()
    return _entry_out(db, entry)


@router.get("/journal-entries", response_model=list[JournalEntryOut])
def list_journal_entries(company_id: uuid.UUID, status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(JournalEntry).filter(JournalEntry.company_id == company_id)
    if status is not None:
        query = query.filter(JournalEntry.status == status)
    entries = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()).all()
    return [_entry_out(db, entry) for entry in entries]


@router.post("/journal-entries/{entry_id}/post", response_model=JournalEntryOut)
def post_journal_entry(entry_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = _get_entry_or_404(db, entry_id)
    try:
        entry = bookkeeping.post_journal_entry(db, entry)
    except bookkeeping.JournalEntryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(
        db, entry.company_id, "journal_entry", entry.id, "post", current_user, f"Posted journal entry {entry.reference or entry.id}"
    )
    db.commit()
    return _entry_out(db, entry)


@router.post("/journal-entries/{entry_id}/reverse", response_model=JournalEntryOut)
def reverse_journal_entry(
    entry_id: uuid.UUID, payload: ReverseJournalEntryIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    entry = _get_entry_or_404(db, entry_id)
    original_reference = entry.reference or str(entry.id)
    original_company_id = entry.company_id
    try:
        reversal = bookkeeping.reverse_journal_entry(db, entry, payload.entry_date)
    except bookkeeping.JournalEntryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(db, original_company_id, "journal_entry", entry_id, "reverse", current_user, f"Reversed journal entry {original_reference}")
    db.commit()
    return _entry_out(db, reversal)


@router.delete("/journal-entries/{entry_id}", status_code=204)
def delete_journal_entry(entry_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = _get_entry_or_404(db, entry_id)
    company_id = entry.company_id
    try:
        bookkeeping.delete_draft_journal_entry(db, entry)
    except bookkeeping.JournalEntryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(db, company_id, "journal_entry", entry_id, "delete", current_user, "Deleted a draft journal entry")
    db.commit()


@router.get("/trial-balance", response_model=TrialBalanceOut)
def get_trial_balance(company_id: uuid.UUID, as_of: date = Query(...), db: Session = Depends(get_db)):
    rows = bookkeeping.trial_balance(db, company_id, as_of)
    total_debit = round(sum(row.total_debit for row in rows), 2)
    total_credit = round(sum(row.total_credit for row in rows), 2)
    return TrialBalanceOut(
        as_of=as_of,
        rows=[TrialBalanceRowOut(**row.__dict__) for row in rows],
        total_debit=total_debit,
        total_credit=total_credit,
        is_balanced=abs(total_debit - total_credit) <= 0.01,
    )
