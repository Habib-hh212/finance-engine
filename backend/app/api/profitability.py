import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.profitability import CustomerProfitabilityOut, ProductProfitabilityOut
from app.services import profitability

router = APIRouter(prefix="/profitability", tags=["profitability"])


@router.get("/by-product", response_model=list[ProductProfitabilityOut])
def get_profitability_by_product(company_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = profitability.by_product(db, company_id)
    return [ProductProfitabilityOut(**row.__dict__) for row in rows]


@router.get("/by-customer", response_model=list[CustomerProfitabilityOut])
def get_profitability_by_customer(company_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = profitability.by_customer(db, company_id)
    return [CustomerProfitabilityOut(**row.__dict__) for row in rows]
