import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Asset, AssetClass, User
from app.models.fixed_asset import DEPRECIATION_METHODS
from app.schemas.fixed_asset import (
    AssetClassCreate,
    AssetClassOut,
    AssetCreate,
    AssetOut,
    AssetRegisterOut,
    AssetRegisterRowOut,
    DepreciationRunOut,
    DepreciationRunRowOut,
    DisposeAssetIn,
    DisposeAssetOut,
    TransferAssetIn,
)
from app.services import audit, fixed_assets
from app.services.bookkeeping import JournalEntryError

router = APIRouter(tags=["fixed-assets"])


def _get_asset_or_404(db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None or asset.company_id != company_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


def _asset_class_out(asset_class: AssetClass) -> AssetClassOut:
    return AssetClassOut(
        id=asset_class.id,
        name=asset_class.name,
        apc_gl_account_id=asset_class.apc_gl_account_id,
        depreciation_expense_gl_account_id=asset_class.depreciation_expense_gl_account_id,
        accumulated_depreciation_gl_account_id=asset_class.accumulated_depreciation_gl_account_id,
        disposal_gain_gl_account_id=asset_class.disposal_gain_gl_account_id,
        disposal_loss_gl_account_id=asset_class.disposal_loss_gl_account_id,
        default_depreciation_method=asset_class.default_depreciation_method,
        default_useful_life_years=float(asset_class.default_useful_life_years),
        default_declining_balance_factor=float(asset_class.default_declining_balance_factor),
    )


def _asset_out(db: Session, asset: Asset, asset_class_name: str) -> AssetOut:
    accumulated = fixed_assets.accumulated_depreciation(db, asset.id)
    return AssetOut(
        id=asset.id,
        asset_class_id=asset.asset_class_id,
        asset_class_name=asset_class_name,
        cost_center_id=asset.cost_center_id,
        code=asset.code,
        name=asset.name,
        acquisition_date=asset.acquisition_date,
        capitalized_cost=float(asset.capitalized_cost),
        salvage_value=float(asset.salvage_value),
        useful_life_years=float(asset.useful_life_years),
        depreciation_method=asset.depreciation_method,
        declining_balance_factor=float(asset.declining_balance_factor),
        status=asset.status,
        disposal_date=asset.disposal_date,
        disposal_proceeds=float(asset.disposal_proceeds) if asset.disposal_proceeds is not None else None,
        disposal_reason=asset.disposal_reason,
        accumulated_depreciation=accumulated,
        net_book_value=round(float(asset.capitalized_cost) - accumulated, 2),
    )


@router.post("/asset-classes", response_model=AssetClassOut)
def create_asset_class(
    company_id: uuid.UUID, payload: AssetClassCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if payload.default_depreciation_method not in DEPRECIATION_METHODS:
        raise HTTPException(status_code=422, detail=f"default_depreciation_method must be one of {sorted(DEPRECIATION_METHODS)}")
    try:
        asset_class = fixed_assets.create_asset_class(db, company_id, **payload.model_dump())
    except fixed_assets.AssetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "asset_class", asset_class.id, "create", current_user, f"Created asset class {asset_class.name}")
    db.commit()
    db.refresh(asset_class)
    return _asset_class_out(asset_class)


@router.get("/asset-classes", response_model=list[AssetClassOut])
def list_asset_classes(company_id: uuid.UUID, db: Session = Depends(get_db)):
    classes = db.query(AssetClass).filter(AssetClass.company_id == company_id).order_by(AssetClass.name).all()
    return [_asset_class_out(c) for c in classes]


@router.post("/assets", response_model=AssetOut)
def create_asset(company_id: uuid.UUID, payload: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.depreciation_method is not None and payload.depreciation_method not in DEPRECIATION_METHODS:
        raise HTTPException(status_code=422, detail=f"depreciation_method must be one of {sorted(DEPRECIATION_METHODS)}")
    try:
        asset = fixed_assets.acquire_asset(db, company_id, **payload.model_dump())
    except (fixed_assets.AssetError, JournalEntryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "asset", asset.id, "create", current_user, f"Acquired asset {asset.code} for {asset.capitalized_cost}")
    db.commit()
    asset_class = db.get(AssetClass, asset.asset_class_id)
    return _asset_out(db, asset, asset_class.name if asset_class else "?")


@router.get("/assets", response_model=list[AssetOut])
def list_assets(company_id: uuid.UUID, status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Asset).filter(Asset.company_id == company_id)
    if status is not None:
        query = query.filter(Asset.status == status)
    assets = query.order_by(Asset.code).all()
    asset_classes = {c.id: c for c in db.query(AssetClass).filter(AssetClass.company_id == company_id).all()}
    return [_asset_out(db, a, asset_classes[a.asset_class_id].name if a.asset_class_id in asset_classes else "?") for a in assets]


@router.get("/assets/register", response_model=AssetRegisterOut)
def get_asset_register(company_id: uuid.UUID, as_of: date = Query(...), db: Session = Depends(get_db)):
    rows = fixed_assets.asset_register(db, company_id, as_of)
    return AssetRegisterOut(
        as_of=as_of,
        rows=[AssetRegisterRowOut(**row.__dict__) for row in rows],
        total_capitalized_cost=round(sum(r.capitalized_cost for r in rows), 2),
        total_accumulated_depreciation=round(sum(r.accumulated_depreciation for r in rows), 2),
        total_net_book_value=round(sum(r.net_book_value for r in rows), 2),
    )


@router.get("/assets/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: uuid.UUID, company_id: uuid.UUID, db: Session = Depends(get_db)):
    asset = _get_asset_or_404(db, company_id, asset_id)
    asset_class = db.get(AssetClass, asset.asset_class_id)
    return _asset_out(db, asset, asset_class.name if asset_class else "?")


@router.post("/assets/{asset_id}/transfer", response_model=AssetOut)
def transfer_asset(
    asset_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TransferAssetIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = _get_asset_or_404(db, company_id, asset_id)
    try:
        asset = fixed_assets.transfer_asset(db, asset, payload.to_cost_center_id)
    except fixed_assets.AssetError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(db, company_id, "asset", asset.id, "transfer", current_user, f"Transferred asset {asset.code}" + (f" -- {payload.reason}" if payload.reason else ""))
    db.commit()
    asset_class = db.get(AssetClass, asset.asset_class_id)
    return _asset_out(db, asset, asset_class.name if asset_class else "?")


@router.post("/assets/{asset_id}/dispose", response_model=DisposeAssetOut)
def dispose_asset(
    asset_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: DisposeAssetIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = _get_asset_or_404(db, company_id, asset_id)
    try:
        asset, gain_or_loss = fixed_assets.dispose_asset(
            db,
            asset,
            payload.disposal_type,
            payload.disposal_date,
            proceeds=payload.proceeds,
            proceeds_gl_account_id=payload.proceeds_gl_account_id,
            reason=payload.reason,
        )
    except fixed_assets.AssetError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.record(
        db,
        company_id,
        "asset",
        asset.id,
        "dispose",
        current_user,
        f"Disposed asset {asset.code} ({payload.disposal_type}), gain/loss {gain_or_loss:.2f}",
    )
    db.commit()
    asset_class = db.get(AssetClass, asset.asset_class_id)
    return DisposeAssetOut(asset=_asset_out(db, asset, asset_class.name if asset_class else "?"), gain_or_loss=gain_or_loss)


@router.post("/assets/depreciation-run", response_model=DepreciationRunOut)
def depreciation_run(
    company_id: uuid.UUID, period: date = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    results = fixed_assets.run_depreciation(db, company_id, period)
    total = round(sum(r.depreciation_amount for r in results), 2)
    audit.record(
        db,
        company_id,
        "asset",
        None,
        "depreciation_run",
        current_user,
        f"Ran depreciation for {date(period.year, period.month, 1).isoformat()}: {total:.2f} total",
    )
    db.commit()
    return DepreciationRunOut(
        period=date(period.year, period.month, 1),
        rows=[DepreciationRunRowOut(**r.__dict__) for r in results],
        total_depreciation=total,
    )


