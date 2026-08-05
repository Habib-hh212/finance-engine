import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class AssetDepreciationGapOut(BaseModel):
    asset_id: uuid.UUID
    code: str


class PeriodCloseStatusOut(BaseModel):
    period: date
    trial_balance_is_balanced: bool
    draft_entries_count: int
    depreciation_run_done: bool
    assets_missing_depreciation: list[AssetDepreciationGapOut]
    accruals_due_for_reversal: int
    ready_to_close: bool


class YearEndCloseIn(BaseModel):
    start: date
    end: date
    retained_earnings_gl_account_id: uuid.UUID


class YearEndCloseOut(BaseModel):
    journal_entry_id: uuid.UUID
    reference: Optional[str]
    net_income: float
    lines_closed: int
