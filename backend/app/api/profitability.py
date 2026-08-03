import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.profitability import CustomerChurnRiskOut, CustomerProfitabilityOut, ProductProfitabilityOut
from app.services import customer_risk, profitability

router = APIRouter(prefix="/profitability", tags=["profitability"])


@router.get("/by-product", response_model=list[ProductProfitabilityOut])
def get_profitability_by_product(company_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = profitability.by_product(db, company_id)
    return [ProductProfitabilityOut(**row.__dict__) for row in rows]


@router.get("/by-customer", response_model=list[CustomerProfitabilityOut])
def get_profitability_by_customer(company_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = profitability.by_customer(db, company_id)
    return [CustomerProfitabilityOut(**row.__dict__) for row in rows]


@router.get("/customer-churn-risk", response_model=list[CustomerChurnRiskOut])
def get_customer_churn_risk(company_id: uuid.UUID, as_of: Optional[date] = Query(None), db: Session = Depends(get_db)):
    rows = customer_risk.compute_churn_risk(db, company_id, as_of=as_of)
    return [CustomerChurnRiskOut(**row.__dict__) for row in rows]
