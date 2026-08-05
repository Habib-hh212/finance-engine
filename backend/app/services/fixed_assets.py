"""Fixed Assets Accounting (SAP calls this sub-ledger "FI-AA"): asset
acquisition, three depreciation methods, transfers, and disposals (sale,
scrap, loss) -- every transaction that changes a company's books posts a
real, balanced journal entry through app/services/bookkeeping.py, so an
asset's history is provable from the general ledger, not a separate set of
numbers that could drift from it.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Asset, AssetClass, DepreciationEntry, GLAccount
from app.models.fixed_asset import AssetStatus, DepreciationMethod
from app.services import bookkeeping


class AssetError(ValueError):
    """Raised when an asset transaction violates a fixed-assets rule."""


def _month_index(acquisition_date: date, period: date) -> int:
    """1 for the acquisition month itself, 2 for the month after, etc.
    Zero or negative means `period` is before the asset was acquired."""
    return (period.year - acquisition_date.year) * 12 + (period.month - acquisition_date.month) + 1


def compute_period_depreciation(asset: Asset, period: date, accumulated_before: float) -> float:
    """The depreciation amount for one asset for one month, under
    whichever method the asset uses. Never returns more than what's left
    to depreciate down to salvage value, and never depreciates a period
    before the asset was acquired."""
    depreciable_base = max(float(asset.capitalized_cost) - float(asset.salvage_value), 0.0)
    remaining = max(depreciable_base - accumulated_before, 0.0)
    if remaining <= 0:
        return 0.0

    month_idx = _month_index(asset.acquisition_date, period)
    total_months = round(float(asset.useful_life_years) * 12)
    if month_idx <= 0 or total_months <= 0:
        return 0.0

    if asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
        if month_idx > total_months:
            return 0.0
        amount = depreciable_base / total_months

    elif asset.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
        # Classic declining-balance: a fixed rate (default double, i.e.
        # factor=2) of the *straight-line* rate, applied each period to
        # whatever book value is left -- not to the original cost -- so
        # the depreciation charge shrinks every period on its own, with no
        # explicit stop date (the floor at salvage_value is what actually
        # ends it).
        monthly_rate = (float(asset.declining_balance_factor) / float(asset.useful_life_years)) / 12
        current_nbv = float(asset.capitalized_cost) - accumulated_before
        amount = max(current_nbv, 0.0) * monthly_rate

    elif asset.depreciation_method == DepreciationMethod.SUM_OF_YEARS_DIGITS:
        # The textbook sum-of-years-digits method, expressed in months
        # instead of years so it lines up with this system's monthly
        # posting periods: month 1 gets total_months/sum(1..total_months)
        # of the depreciable base, month 2 gets (total_months-1)/sum, etc.
        if month_idx > total_months:
            return 0.0
        remaining_months = total_months - month_idx + 1
        syd_sum = total_months * (total_months + 1) / 2
        amount = depreciable_base * remaining_months / syd_sum

    else:
        raise AssetError(f"Unknown depreciation method '{asset.depreciation_method}'.")

    return round(min(amount, remaining), 2)


def create_asset_class(
    db: Session,
    company_id,
    name: str,
    apc_gl_account_id,
    depreciation_expense_gl_account_id,
    accumulated_depreciation_gl_account_id,
    disposal_gain_gl_account_id,
    disposal_loss_gl_account_id,
    default_depreciation_method: str = DepreciationMethod.STRAIGHT_LINE,
    default_useful_life_years: float = 5,
    default_declining_balance_factor: float = 2.0,
) -> AssetClass:
    accounts = {a.id for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    for gl_id in (
        apc_gl_account_id,
        depreciation_expense_gl_account_id,
        accumulated_depreciation_gl_account_id,
        disposal_gain_gl_account_id,
        disposal_loss_gl_account_id,
    ):
        if gl_id not in accounts:
            raise AssetError("An asset class G/L account doesn't belong to this company.")

    asset_class = AssetClass(
        company_id=company_id,
        name=name,
        apc_gl_account_id=apc_gl_account_id,
        depreciation_expense_gl_account_id=depreciation_expense_gl_account_id,
        accumulated_depreciation_gl_account_id=accumulated_depreciation_gl_account_id,
        disposal_gain_gl_account_id=disposal_gain_gl_account_id,
        disposal_loss_gl_account_id=disposal_loss_gl_account_id,
        default_depreciation_method=default_depreciation_method,
        default_useful_life_years=default_useful_life_years,
        default_declining_balance_factor=default_declining_balance_factor,
    )
    db.add(asset_class)
    db.commit()
    db.refresh(asset_class)
    return asset_class


def acquire_asset(
    db: Session,
    company_id,
    asset_class_id,
    code: str,
    name: str,
    acquisition_date: date,
    capitalized_cost: float,
    funding_gl_account_id,
    salvage_value: float = 0,
    useful_life_years: Optional[float] = None,
    depreciation_method: Optional[str] = None,
    declining_balance_factor: Optional[float] = None,
    cost_center_id=None,
) -> Asset:
    asset_class = db.get(AssetClass, asset_class_id)
    if asset_class is None or asset_class.company_id != company_id:
        raise AssetError("Asset class not found in this company.")
    if capitalized_cost <= 0:
        raise AssetError("Capitalized cost must be positive.")
    if salvage_value < 0 or salvage_value >= capitalized_cost:
        raise AssetError("Salvage value must be zero or positive and less than the capitalized cost.")

    accounts = {a.id for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    if funding_gl_account_id not in accounts:
        raise AssetError("The funding G/L account doesn't belong to this company.")

    asset = Asset(
        company_id=company_id,
        asset_class_id=asset_class_id,
        cost_center_id=cost_center_id,
        code=code,
        name=name,
        acquisition_date=acquisition_date,
        capitalized_cost=capitalized_cost,
        salvage_value=salvage_value,
        useful_life_years=useful_life_years if useful_life_years is not None else asset_class.default_useful_life_years,
        depreciation_method=depreciation_method or asset_class.default_depreciation_method,
        declining_balance_factor=declining_balance_factor
        if declining_balance_factor is not None
        else asset_class.default_declining_balance_factor,
        status=AssetStatus.ACTIVE,
    )
    db.add(asset)
    db.flush()

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        acquisition_date,
        [
            bookkeeping.LineInput(gl_account_id=asset_class.apc_gl_account_id, debit_amount=capitalized_cost, cost_center_id=cost_center_id),
            bookkeeping.LineInput(gl_account_id=funding_gl_account_id, credit_amount=capitalized_cost),
        ],
        reference=f"Asset acquisition: {code}",
        description=f"Capitalized {name}",
        currency="USD",
    )
    entry = bookkeeping.post_journal_entry(db, entry)
    asset.acquisition_journal_entry_id = entry.id
    db.commit()
    db.refresh(asset)
    return asset


def accumulated_depreciation(db: Session, asset_id) -> float:
    total = 0.0
    for row in db.query(DepreciationEntry).filter(DepreciationEntry.asset_id == asset_id).all():
        total += float(row.depreciation_amount)
    return round(total, 2)


@dataclass
class DepreciationRunResult:
    asset_id: object
    asset_code: str
    depreciation_amount: float
    skipped_reason: Optional[str] = None


def run_depreciation(db: Session, company_id, period: date) -> list:
    """Depreciate every active asset for one period (a calendar month).
    Idempotent -- an asset already depreciated for this exact period is
    skipped, not double-posted -- so re-running the same period is safe."""
    period = date(period.year, period.month, 1)
    assets = (
        db.query(Asset)
        .filter(Asset.company_id == company_id, Asset.status == AssetStatus.ACTIVE)
        .order_by(Asset.code)
        .all()
    )
    asset_classes = {ac.id: ac for ac in db.query(AssetClass).filter(AssetClass.company_id == company_id).all()}

    results = []
    for asset in assets:
        already = (
            db.query(DepreciationEntry)
            .filter(DepreciationEntry.asset_id == asset.id, DepreciationEntry.period == period)
            .first()
        )
        if already is not None:
            results.append(DepreciationRunResult(asset.id, asset.code, 0.0, skipped_reason="Already depreciated for this period."))
            continue

        accumulated_before = accumulated_depreciation(db, asset.id)
        amount = compute_period_depreciation(asset, period, accumulated_before)
        if amount <= 0:
            results.append(DepreciationRunResult(asset.id, asset.code, 0.0, skipped_reason="Nothing to depreciate for this period."))
            continue

        asset_class = asset_classes[asset.asset_class_id]
        entry = bookkeeping.create_journal_entry(
            db,
            company_id,
            period,
            [
                bookkeeping.LineInput(
                    gl_account_id=asset_class.depreciation_expense_gl_account_id,
                    debit_amount=amount,
                    cost_center_id=asset.cost_center_id,
                ),
                bookkeeping.LineInput(gl_account_id=asset_class.accumulated_depreciation_gl_account_id, credit_amount=amount),
            ],
            reference=f"Depreciation: {asset.code}",
            description=f"{period.isoformat()} depreciation for {asset.name}",
            currency="USD",
        )
        entry = bookkeeping.post_journal_entry(db, entry)

        new_accumulated = round(accumulated_before + amount, 2)
        db.add(
            DepreciationEntry(
                asset_id=asset.id,
                period=period,
                depreciation_amount=amount,
                accumulated_depreciation_after=new_accumulated,
                net_book_value_after=round(float(asset.capitalized_cost) - new_accumulated, 2),
                journal_entry_id=entry.id,
            )
        )
        results.append(DepreciationRunResult(asset.id, asset.code, amount))

    db.commit()
    return results


def transfer_asset(db: Session, asset: Asset, to_cost_center_id) -> Asset:
    if asset.status != AssetStatus.ACTIVE:
        raise AssetError(f"Only an active asset can be transferred (this one is '{asset.status}').")
    asset.cost_center_id = to_cost_center_id
    db.commit()
    db.refresh(asset)
    return asset


DISPOSAL_TO_STATUS = {"sale": AssetStatus.SOLD, "scrap": AssetStatus.SCRAPPED, "lost": AssetStatus.LOST}


def dispose_asset(
    db: Session,
    asset: Asset,
    disposal_type: str,
    disposal_date: date,
    proceeds: float = 0.0,
    proceeds_gl_account_id=None,
    reason: Optional[str] = None,
):
    if asset.status != AssetStatus.ACTIVE:
        raise AssetError(f"Only an active asset can be disposed (this one is '{asset.status}').")
    if disposal_type not in DISPOSAL_TO_STATUS:
        raise AssetError(f"disposal_type must be one of {sorted(DISPOSAL_TO_STATUS)}")
    if proceeds < 0:
        raise AssetError("Proceeds can't be negative.")
    if proceeds > 0 and proceeds_gl_account_id is None:
        raise AssetError("A G/L account is required to record disposal proceeds.")

    asset_class = db.get(AssetClass, asset.asset_class_id)
    accumulated = accumulated_depreciation(db, asset.id)
    net_book_value = round(float(asset.capitalized_cost) - accumulated, 2)
    gain_or_loss = round(proceeds - net_book_value, 2)

    lines = [bookkeeping.LineInput(gl_account_id=asset_class.apc_gl_account_id, credit_amount=float(asset.capitalized_cost))]
    if accumulated > 0:
        lines.append(bookkeeping.LineInput(gl_account_id=asset_class.accumulated_depreciation_gl_account_id, debit_amount=accumulated))
    if proceeds > 0:
        lines.append(bookkeeping.LineInput(gl_account_id=proceeds_gl_account_id, debit_amount=proceeds))
    if gain_or_loss > 0:
        lines.append(bookkeeping.LineInput(gl_account_id=asset_class.disposal_gain_gl_account_id, credit_amount=gain_or_loss))
    elif gain_or_loss < 0:
        lines.append(bookkeeping.LineInput(gl_account_id=asset_class.disposal_loss_gl_account_id, debit_amount=abs(gain_or_loss)))

    entry = bookkeeping.create_journal_entry(
        db,
        asset.company_id,
        disposal_date,
        lines,
        reference=f"Disposal ({disposal_type}): {asset.code}",
        description=reason or f"{disposal_type} of {asset.name}",
        currency="USD",
    )
    bookkeeping.post_journal_entry(db, entry)

    asset.status = DISPOSAL_TO_STATUS[disposal_type]
    asset.disposal_date = disposal_date
    asset.disposal_proceeds = proceeds
    asset.disposal_reason = reason
    db.commit()
    db.refresh(asset)
    return asset, gain_or_loss


@dataclass
class AssetRegisterRow:
    asset_id: object
    code: str
    name: str
    asset_class_name: str
    status: str
    acquisition_date: date
    capitalized_cost: float
    accumulated_depreciation: float
    net_book_value: float


def asset_register(db: Session, company_id, as_of: date) -> list:
    """The classic Fixed Asset Register -- every asset, its cost,
    accumulated depreciation as of a date, and net book value. What a
    Trial Balance is to the general ledger, this is to the asset
    sub-ledger."""
    assets = db.query(Asset).filter(Asset.company_id == company_id, Asset.acquisition_date <= as_of).order_by(Asset.code).all()
    asset_classes = {ac.id: ac for ac in db.query(AssetClass).filter(AssetClass.company_id == company_id).all()}

    rows = []
    for asset in assets:
        entries = (
            db.query(DepreciationEntry)
            .filter(DepreciationEntry.asset_id == asset.id, DepreciationEntry.period <= as_of)
            .all()
        )
        accumulated = round(sum(float(e.depreciation_amount) for e in entries), 2)
        rows.append(
            AssetRegisterRow(
                asset_id=asset.id,
                code=asset.code,
                name=asset.name,
                asset_class_name=asset_classes[asset.asset_class_id].name if asset.asset_class_id in asset_classes else "?",
                status=asset.status,
                acquisition_date=asset.acquisition_date,
                capitalized_cost=float(asset.capitalized_cost),
                accumulated_depreciation=accumulated,
                net_book_value=round(float(asset.capitalized_cost) - accumulated, 2),
            )
        )
    return rows
