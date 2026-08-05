import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.period_close import (
    AssetDepreciationGapOut,
    PeriodCloseStatusOut,
    YearEndCloseIn,
    YearEndCloseOut,
)
from app.services import audit, period_close

router = APIRouter(tags=["period-close"])


@router.get("/period-close/status", response_model=PeriodCloseStatusOut)
def get_period_close_status(company_id: uuid.UUID, period: date = Query(...), db: Session = Depends(get_db)):
    result = period_close.period_close_status(db, company_id, period)
    ready = (
        result.trial_balance_is_balanced
        and result.draft_entries_count == 0
        and result.depreciation_run_done
        and not result.assets_missing_depreciation
        and result.accruals_due_for_reversal == 0
    )
    return PeriodCloseStatusOut(
        period=result.period,
        trial_balance_is_balanced=result.trial_balance_is_balanced,
        draft_entries_count=result.draft_entries_count,
        depreciation_run_done=result.depreciation_run_done,
        assets_missing_depreciation=[AssetDepreciationGapOut(**g.__dict__) for g in result.assets_missing_depreciation],
        accruals_due_for_reversal=result.accruals_due_for_reversal,
        ready_to_close=ready,
    )


@router.post("/year-end/close", response_model=YearEndCloseOut)
def close_fiscal_year(
    company_id: uuid.UUID, payload: YearEndCloseIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        entry, net_income, lines_count = period_close.close_fiscal_year(
            db, company_id, payload.start, payload.end, payload.retained_earnings_gl_account_id
        )
    except period_close.PeriodCloseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "year_end_close", entry.id, "close", current_user, f"Closed FY ending {payload.end}: net income {net_income:.2f}")
    db.commit()
    return YearEndCloseOut(journal_entry_id=entry.id, reference=entry.reference, net_income=net_income, lines_closed=lines_count)
