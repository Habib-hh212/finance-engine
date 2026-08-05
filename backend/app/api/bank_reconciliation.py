import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import BankStatementLine, User
from app.schemas.bank_reconciliation import (
    BankImportResultOut,
    BankStatementLineOut,
    ManualMatchIn,
    ReconciliationSummaryOut,
    UnmatchedGLLineOut,
)
from app.services import audit
from app.services import bank_reconciliation as bankrec

router = APIRouter(tags=["bank-reconciliation"])


def _get_line_or_404(db: Session, company_id: uuid.UUID, line_id: uuid.UUID) -> BankStatementLine:
    line = db.get(BankStatementLine, line_id)
    if line is None or line.company_id != company_id:
        raise HTTPException(status_code=404, detail="Bank statement line not found")
    return line


def _line_out(line: BankStatementLine) -> BankStatementLineOut:
    return BankStatementLineOut(
        id=line.id,
        cash_gl_account_id=line.cash_gl_account_id,
        statement_date=line.statement_date,
        description=line.description,
        amount=float(line.amount),
        reference=line.reference,
        matched_actual_line_id=line.matched_actual_line_id,
        match_type=line.match_type,
    )


@router.post("/bank-statements/upload", response_model=BankImportResultOut)
async def upload_bank_statement(
    cash_gl_account_id: uuid.UUID,
    file: UploadFile,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, or .csv files are supported")
    contents = await file.read()
    try:
        result = bankrec.import_bank_statement(db, company_id, cash_gl_account_id, contents, file.filename)
    except bankrec.BankReconciliationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(
        db, company_id, "bank_statement", None, "import", current_user, f"Imported {result.rows_imported} bank statement line(s), {result.auto_matched} auto-matched"
    )
    db.commit()
    return BankImportResultOut(rows_imported=result.rows_imported, auto_matched=result.auto_matched)


@router.get("/bank-statements", response_model=list[BankStatementLineOut])
def list_bank_statement_lines(cash_gl_account_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    lines = (
        db.query(BankStatementLine)
        .filter(BankStatementLine.company_id == company_id, BankStatementLine.cash_gl_account_id == cash_gl_account_id)
        .order_by(BankStatementLine.statement_date.desc())
        .all()
    )
    return [_line_out(line) for line in lines]


@router.post("/bank-statements/{line_id}/match", response_model=BankStatementLineOut)
def match_bank_statement_line(
    line_id: uuid.UUID,
    payload: ManualMatchIn,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    line = _get_line_or_404(db, company_id, line_id)
    try:
        line = bankrec.manual_match(db, line, payload.actual_line_id)
    except bankrec.BankReconciliationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "bank_statement", line.id, "match", current_user, "Manually matched a bank statement line")
    db.commit()
    return _line_out(line)


@router.post("/bank-statements/{line_id}/unmatch", response_model=BankStatementLineOut)
def unmatch_bank_statement_line(line_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    line = _get_line_or_404(db, company_id, line_id)
    try:
        line = bankrec.unmatch(db, line)
    except bankrec.BankReconciliationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(db, company_id, "bank_statement", line.id, "unmatch", current_user, "Unmatched a bank statement line")
    db.commit()
    return _line_out(line)


@router.delete("/bank-statements/{line_id}", status_code=204)
def delete_bank_statement_line(line_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    line = _get_line_or_404(db, company_id, line_id)
    try:
        bankrec.delete_bank_line(db, line)
    except bankrec.BankReconciliationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(db, company_id, "bank_statement", line_id, "delete", current_user, "Deleted an unmatched bank statement line")
    db.commit()


@router.get("/bank-reconciliation/unmatched-gl-lines", response_model=list[UnmatchedGLLineOut])
def get_unmatched_gl_lines(cash_gl_account_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    rows = bankrec.unmatched_gl_lines(db, company_id, cash_gl_account_id)
    return [UnmatchedGLLineOut(**row.__dict__) for row in rows]


@router.get("/bank-reconciliation/summary", response_model=ReconciliationSummaryOut)
def get_reconciliation_summary(
    cash_gl_account_id: uuid.UUID,
    company_id: uuid.UUID = Depends(require_company_access),
    as_of: date = Query(...),
    bank_statement_ending_balance: float = Query(...),
    db: Session = Depends(get_db)):
    try:
        result = bankrec.reconciliation_summary(db, company_id, cash_gl_account_id, as_of, bank_statement_ending_balance)
    except bankrec.BankReconciliationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ReconciliationSummaryOut(**result.__dict__)
