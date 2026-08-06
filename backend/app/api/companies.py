import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_resource_company_access
from app.database import get_db
from app.models import Company, CompanyMembership, User
from app.schemas.sales import CompanyCreate, CompanyOut, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = Company(name=payload.name, base_currency=payload.base_currency.upper(), home_state=payload.home_state)
    db.add(company)
    db.flush()
    db.add(CompanyMembership(company_id=company.id, user_id=current_user.id))
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(company_id: uuid.UUID, payload: CompanyUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_resource_company_access(db, current_user, company.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Company)
        .join(CompanyMembership, CompanyMembership.company_id == Company.id)
        .filter(CompanyMembership.user_id == current_user.id)
        .all()
    )
