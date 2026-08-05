import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import TAX_DIRECTIONS, TAX_TYPES, GLAccount, TaxCode, User
from app.schemas.tax_code import TaxCodeCreate, TaxCodeOut, TaxCodeUpdate, TaxReportOut, TaxReportRowOut
from app.services import audit, tax_reporting

router = APIRouter(tags=["tax-codes"])


def _account_or_422(db: Session, company_id: uuid.UUID, gl_account_id: uuid.UUID) -> GLAccount:
    account = db.get(GLAccount, gl_account_id)
    if account is None or account.company_id != company_id:
        raise HTTPException(status_code=422, detail="Tax G/L account doesn't belong to this company.")
    return account


def _tax_code_out(tax_code: TaxCode, account: GLAccount) -> TaxCodeOut:
    return TaxCodeOut(
        id=tax_code.id,
        country=tax_code.country,
        code=tax_code.code,
        name=tax_code.name,
        tax_type=tax_code.tax_type,
        rate_pct=float(tax_code.rate_pct),
        direction=tax_code.direction,
        gl_account_id=tax_code.gl_account_id,
        gl_account_code=account.code,
        gl_account_name=account.name,
        is_active=tax_code.is_active,
    )


@router.post("/tax-codes", response_model=TaxCodeOut)
def create_tax_code( payload: TaxCodeCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if payload.tax_type not in TAX_TYPES:
        raise HTTPException(status_code=422, detail=f"tax_type must be one of {sorted(TAX_TYPES)}")
    if payload.direction not in TAX_DIRECTIONS:
        raise HTTPException(status_code=422, detail=f"direction must be one of {sorted(TAX_DIRECTIONS)}")
    if payload.rate_pct < 0:
        raise HTTPException(status_code=422, detail="rate_pct can't be negative.")
    account = _account_or_422(db, company_id, payload.gl_account_id)

    tax_code = TaxCode(company_id=company_id, **payload.model_dump())
    db.add(tax_code)
    db.flush()
    audit.record(db, company_id, "tax_code", tax_code.id, "create", current_user, f"Created tax code {tax_code.code} ({tax_code.rate_pct}%)")
    db.commit()
    db.refresh(tax_code)
    return _tax_code_out(tax_code, account)


@router.get("/tax-codes", response_model=list[TaxCodeOut])
def list_tax_codes(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    codes = db.query(TaxCode).filter(TaxCode.company_id == company_id).order_by(TaxCode.country, TaxCode.code).all()
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    return [_tax_code_out(c, accounts[c.gl_account_id]) for c in codes]


@router.patch("/tax-codes/{tax_code_id}", response_model=TaxCodeOut)
def update_tax_code(
    tax_code_id: uuid.UUID,
    payload: TaxCodeUpdate,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    tax_code = db.get(TaxCode, tax_code_id)
    if tax_code is None or tax_code.company_id != company_id:
        raise HTTPException(status_code=404, detail="Tax code not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tax_code, field, value)
    db.flush()
    audit.record(db, company_id, "tax_code", tax_code.id, "update", current_user, f"Updated tax code {tax_code.code}")
    db.commit()
    db.refresh(tax_code)
    account = _account_or_422(db, company_id, tax_code.gl_account_id)
    return _tax_code_out(tax_code, account)


@router.get("/tax-report", response_model=TaxReportOut)
def get_tax_report(
    company_id: uuid.UUID = Depends(require_company_access), start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)
):
    result = tax_reporting.tax_report(db, company_id, start, end)
    return TaxReportOut(
        start=start,
        end=end,
        rows=[TaxReportRowOut(**row.__dict__) for row in result.rows],
        total_output_tax=result.total_output_tax,
        total_input_tax=result.total_input_tax,
        net_tax_payable=result.net_tax_payable,
    )
