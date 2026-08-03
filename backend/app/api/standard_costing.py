import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductionActual, StandardCost
from app.schemas.standard_costing import (
    ProductionActualIn,
    ProductionActualOut,
    StandardCostIn,
    StandardCostOut,
    StandardCostVarianceOut,
)
from app.services import standard_costing

router = APIRouter(tags=["standard-costing"])


@router.post("/standard-costs", response_model=StandardCostOut)
def upsert_standard_cost(company_id: uuid.UUID, payload: StandardCostIn, db: Session = Depends(get_db)):
    existing = (
        db.query(StandardCost)
        .filter(StandardCost.company_id == company_id, StandardCost.product_id == payload.product_id)
        .first()
    )
    if existing is not None:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        record = existing
    else:
        record = StandardCost(company_id=company_id, **payload.model_dump())
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/standard-costs", response_model=list[StandardCostOut])
def list_standard_costs(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(StandardCost).filter(StandardCost.company_id == company_id).all()


@router.post("/production-actuals", response_model=ProductionActualOut)
def create_production_actual(company_id: uuid.UUID, payload: ProductionActualIn, db: Session = Depends(get_db)):
    record = ProductionActual(company_id=company_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/production-actuals", response_model=list[ProductionActualOut])
def list_production_actuals(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(ProductionActual).filter(ProductionActual.company_id == company_id).all()


@router.get("/standard-costing/variance", response_model=list[StandardCostVarianceOut])
def get_standard_cost_variance(company_id: uuid.UUID, fiscal_year: Optional[int] = Query(None), db: Session = Depends(get_db)):
    rows = standard_costing.variance_for_company(db, company_id, fiscal_year=fiscal_year)
    return [StandardCostVarianceOut(**row.__dict__) for row in rows]
