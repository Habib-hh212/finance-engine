import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.insights import InsightOut
from app.services import insights

router = APIRouter(tags=["ai-insights"])


@router.get("/ai/insights", response_model=list[InsightOut])
def get_insights(company_id: uuid.UUID, fiscal_year: Optional[int] = Query(None), db: Session = Depends(get_db)):
    rows = insights.generate_insights(db, company_id, fiscal_year=fiscal_year)
    return [InsightOut(**row.__dict__) for row in rows]
