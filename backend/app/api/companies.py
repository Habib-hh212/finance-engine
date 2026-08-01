from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company
from app.schemas.sales import CompanyCreate, CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(name=payload.name, base_currency=payload.base_currency.upper())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()
