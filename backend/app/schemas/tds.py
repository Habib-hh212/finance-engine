import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class TdsSectionCreate(BaseModel):
    section_code: str
    description: str
    rate_pct: float


class TdsSectionUpdate(BaseModel):
    description: Optional[str] = None
    rate_pct: Optional[float] = None
    is_active: Optional[bool] = None


class TdsSectionOut(BaseModel):
    id: uuid.UUID
    section_code: str
    description: str
    rate_pct: float
    is_active: bool

    model_config = {"from_attributes": True}


class TdsSectionSummaryRowOut(BaseModel):
    tds_section_id: uuid.UUID
    section_code: str
    description: str
    rate_pct: float
    gross_amount: float
    tds_amount: float


class TdsDeducteeSummaryRowOut(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str
    gross_amount: float
    tds_amount: float


class TdsSummaryOut(BaseModel):
    start: date
    end: date
    section_rows: list[TdsSectionSummaryRowOut]
    deductee_rows: list[TdsDeducteeSummaryRowOut]
    total_tds: float
