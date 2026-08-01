import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.product import ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.company_id == company_id).all()


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.unit_variable_cost = payload.unit_variable_cost
    db.commit()
    db.refresh(product)
    return product
