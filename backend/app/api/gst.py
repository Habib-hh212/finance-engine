import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import GST_DIRECTIONS, GstRate, User
from app.schemas.gst import (
    Gstr1B2BRowOut,
    Gstr1B2CRowOut,
    Gstr1HsnRowOut,
    Gstr1Out,
    Gstr3bOut,
    GstRateCreate,
    GstRateOut,
    GstRateUpdate,
)
from app.services import audit, gst

router = APIRouter(tags=["gst"])


@router.post("/gst-rates", response_model=GstRateOut)
def create_gst_rate(
    payload: GstRateCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if payload.rate_pct < 0:
        raise HTTPException(status_code=422, detail="rate_pct can't be negative.")
    if payload.direction not in GST_DIRECTIONS:
        raise HTTPException(status_code=422, detail=f"direction must be one of {sorted(GST_DIRECTIONS)}")
    rate = GstRate(company_id=company_id, **payload.model_dump())
    db.add(rate)
    db.flush()
    audit.record(db, company_id, "gst_rate", rate.id, "create", current_user, f"Created GST rate {rate.description} ({rate.rate_pct}%)")
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/gst-rates", response_model=list[GstRateOut])
def list_gst_rates(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(GstRate).filter(GstRate.company_id == company_id).order_by(GstRate.description).all()


@router.patch("/gst-rates/{rate_id}", response_model=GstRateOut)
def update_gst_rate(
    rate_id: uuid.UUID,
    payload: GstRateUpdate,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rate = db.get(GstRate, rate_id)
    if rate is None or rate.company_id != company_id:
        raise HTTPException(status_code=404, detail="GST rate not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)
    db.flush()
    audit.record(db, company_id, "gst_rate", rate.id, "update", current_user, f"Updated GST rate {rate.description}")
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/gstr1-report", response_model=Gstr1Out)
def get_gstr1_report(company_id: uuid.UUID = Depends(require_company_access), start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    result = gst.gstr1_report(db, company_id, start, end)
    return Gstr1Out(
        start=start,
        end=end,
        b2b_rows=[Gstr1B2BRowOut(**row.__dict__) for row in result.b2b_rows],
        b2c_rows=[Gstr1B2CRowOut(**row.__dict__) for row in result.b2c_rows],
        hsn_rows=[Gstr1HsnRowOut(**row.__dict__) for row in result.hsn_rows],
        total_taxable_value=result.total_taxable_value,
        total_tax=result.total_tax,
    )


@router.get("/gstr3b-report", response_model=Gstr3bOut)
def get_gstr3b_report(company_id: uuid.UUID = Depends(require_company_access), start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    result = gst.gstr3b_report(db, company_id, start, end)
    return Gstr3bOut(start=start, end=end, **result.__dict__)
