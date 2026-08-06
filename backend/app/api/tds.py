import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import TdsSection, User
from app.schemas.tds import (
    TdsDeducteeSummaryRowOut,
    TdsSectionCreate,
    TdsSectionOut,
    TdsSectionSummaryRowOut,
    TdsSectionUpdate,
    TdsSummaryOut,
)
from app.services import audit, tds

router = APIRouter(tags=["tds"])


@router.post("/tds-sections", response_model=TdsSectionOut)
def create_tds_section(
    payload: TdsSectionCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if payload.rate_pct < 0:
        raise HTTPException(status_code=422, detail="rate_pct can't be negative.")
    section = TdsSection(company_id=company_id, **payload.model_dump())
    db.add(section)
    db.flush()
    audit.record(db, company_id, "tds_section", section.id, "create", current_user, f"Created TDS section {section.section_code} ({section.rate_pct}%)")
    db.commit()
    db.refresh(section)
    return section


@router.get("/tds-sections", response_model=list[TdsSectionOut])
def list_tds_sections(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(TdsSection).filter(TdsSection.company_id == company_id).order_by(TdsSection.section_code).all()


@router.patch("/tds-sections/{section_id}", response_model=TdsSectionOut)
def update_tds_section(
    section_id: uuid.UUID,
    payload: TdsSectionUpdate,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    section = db.get(TdsSection, section_id)
    if section is None or section.company_id != company_id:
        raise HTTPException(status_code=404, detail="TDS section not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(section, field, value)
    db.flush()
    audit.record(db, company_id, "tds_section", section.id, "update", current_user, f"Updated TDS section {section.section_code}")
    db.commit()
    db.refresh(section)
    return section


@router.get("/tds-report", response_model=TdsSummaryOut)
def get_tds_report(company_id: uuid.UUID = Depends(require_company_access), start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    result = tds.tds_summary(db, company_id, start, end)
    return TdsSummaryOut(
        start=start,
        end=end,
        section_rows=[TdsSectionSummaryRowOut(**row.__dict__) for row in result.section_rows],
        deductee_rows=[TdsDeducteeSummaryRowOut(**row.__dict__) for row in result.deductee_rows],
        total_tds=result.total_tds,
    )
