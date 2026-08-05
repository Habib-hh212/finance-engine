import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class AssetClassCreate(BaseModel):
    name: str
    apc_gl_account_id: uuid.UUID
    depreciation_expense_gl_account_id: uuid.UUID
    accumulated_depreciation_gl_account_id: uuid.UUID
    disposal_gain_gl_account_id: uuid.UUID
    disposal_loss_gl_account_id: uuid.UUID
    default_depreciation_method: str = "straight_line"
    default_useful_life_years: float = 5
    default_declining_balance_factor: float = 2.0


class AssetClassOut(BaseModel):
    id: uuid.UUID
    name: str
    apc_gl_account_id: uuid.UUID
    depreciation_expense_gl_account_id: uuid.UUID
    accumulated_depreciation_gl_account_id: uuid.UUID
    disposal_gain_gl_account_id: uuid.UUID
    disposal_loss_gl_account_id: uuid.UUID
    default_depreciation_method: str
    default_useful_life_years: float
    default_declining_balance_factor: float


class AssetCreate(BaseModel):
    asset_class_id: uuid.UUID
    code: str
    name: str
    acquisition_date: date
    capitalized_cost: float
    funding_gl_account_id: uuid.UUID
    salvage_value: float = 0
    useful_life_years: Optional[float] = None
    depreciation_method: Optional[str] = None
    declining_balance_factor: Optional[float] = None
    cost_center_id: Optional[uuid.UUID] = None


class AssetOut(BaseModel):
    id: uuid.UUID
    asset_class_id: uuid.UUID
    asset_class_name: str
    cost_center_id: Optional[uuid.UUID]
    code: str
    name: str
    acquisition_date: date
    capitalized_cost: float
    salvage_value: float
    useful_life_years: float
    depreciation_method: str
    declining_balance_factor: float
    status: str
    disposal_date: Optional[date]
    disposal_proceeds: Optional[float]
    disposal_reason: Optional[str]
    accumulated_depreciation: float
    net_book_value: float


class TransferAssetIn(BaseModel):
    to_cost_center_id: uuid.UUID
    reason: Optional[str] = None


class DisposeAssetIn(BaseModel):
    disposal_type: str
    disposal_date: date
    proceeds: float = 0
    proceeds_gl_account_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None


class DisposeAssetOut(BaseModel):
    asset: AssetOut
    gain_or_loss: float


class DepreciationRunRowOut(BaseModel):
    asset_id: uuid.UUID
    asset_code: str
    depreciation_amount: float
    skipped_reason: Optional[str] = None


class DepreciationRunOut(BaseModel):
    period: date
    rows: list[DepreciationRunRowOut]
    total_depreciation: float


class AssetRegisterRowOut(BaseModel):
    asset_id: uuid.UUID
    code: str
    name: str
    asset_class_name: str
    status: str
    acquisition_date: date
    capitalized_cost: float
    accumulated_depreciation: float
    net_book_value: float


class AssetRegisterOut(BaseModel):
    as_of: date
    rows: list[AssetRegisterRowOut]
    total_capitalized_cost: float
    total_accumulated_depreciation: float
    total_net_book_value: float
