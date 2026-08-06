"""Section 192 of India's Income Tax Act: an employer must estimate each
employee's total tax for the financial year and deduct it in roughly equal
monthly instalments from salary -- a completely different mechanism from
the flat-rate TDS in tds.py, which deducts a fixed percentage on a vendor
bill regardless of the vendor's total income. Salary TDS needs the
employee's *annual* projected income, their chosen regime (old regime keeps
Chapter VI-A deductions and HRA exemption; the new regime is a simpler slab
table with just a standard deduction), and applies actual progressive
slabs plus a Section 87A rebate and 4% health & education cess.

Rates below are FY 2025-26 (Finance Act 2025) -- these change every Union
Budget, so this is the one place in the module that will need a yearly
update, same as tds.py's TdsSection rates need reviewing when the
government revises them.

Simplifications, called out so they don't get mistaken for a full payroll
engine: no surcharge for very high incomes, no marginal relief at the
rebate cliff-edge, EPF wage ceiling not modelled, and monthly TDS is
annual tax / 12 recomputed fresh each run rather than re-projected off
months actually remaining in the FY.
"""
from dataclasses import dataclass

STANDARD_DEDUCTION_OLD = 50_000.0
STANDARD_DEDUCTION_NEW = 75_000.0
SECTION_80C_CAP = 150_000.0
SECTION_80D_CAP = 25_000.0
HOME_LOAN_INTEREST_CAP = 200_000.0
CESS_RATE = 0.04

# (slab floor, slab rate) -- the rate applies to income above this floor and
# up to the next slab's floor.
OLD_REGIME_SLABS = [
    (0.0, 0.0),
    (250_000.0, 0.05),
    (500_000.0, 0.20),
    (1_000_000.0, 0.30),
]
OLD_REGIME_REBATE_CEILING = 500_000.0
OLD_REGIME_REBATE_MAX = 12_500.0

NEW_REGIME_SLABS = [
    (0.0, 0.0),
    (400_000.0, 0.05),
    (800_000.0, 0.10),
    (1_200_000.0, 0.15),
    (1_600_000.0, 0.20),
    (2_000_000.0, 0.25),
    (2_400_000.0, 0.30),
]
NEW_REGIME_REBATE_CEILING = 1_200_000.0
NEW_REGIME_REBATE_MAX = 60_000.0


def _slab_tax(taxable_income: float, slabs: list[tuple[float, float]]) -> float:
    if taxable_income <= 0:
        return 0.0
    tax = 0.0
    for i, (floor, rate) in enumerate(slabs):
        next_floor = slabs[i + 1][0] if i + 1 < len(slabs) else None
        if taxable_income <= floor:
            break
        band_top = min(taxable_income, next_floor) if next_floor is not None else taxable_income
        tax += (band_top - floor) * rate
    return tax


def compute_annual_tax(taxable_income: float, regime: str) -> float:
    """Tax payable for the year, after the Section 87A rebate and 4% cess."""
    taxable_income = max(0.0, round(taxable_income, 2))
    if regime == "old":
        tax = _slab_tax(taxable_income, OLD_REGIME_SLABS)
        if taxable_income <= OLD_REGIME_REBATE_CEILING:
            tax = max(0.0, tax - min(tax, OLD_REGIME_REBATE_MAX))
    else:
        tax = _slab_tax(taxable_income, NEW_REGIME_SLABS)
        if taxable_income <= NEW_REGIME_REBATE_CEILING:
            tax = max(0.0, tax - min(tax, NEW_REGIME_REBATE_MAX))
    return round(tax * (1 + CESS_RATE), 2)


def hra_exemption(basic_annual: float, hra_received_annual: float, rent_paid_annual: float, is_metro: bool) -> float:
    """The least of: HRA actually received, rent paid minus 10% of basic, or
    50%/40% of basic (metro/non-metro) -- Section 10(13A). Old regime only;
    the new regime doesn't exempt HRA at all."""
    if rent_paid_annual <= 0 or hra_received_annual <= 0:
        return 0.0
    rent_over_basic = max(0.0, rent_paid_annual - 0.10 * basic_annual)
    pct_of_basic = (0.50 if is_metro else 0.40) * basic_annual
    return round(max(0.0, min(hra_received_annual, rent_over_basic, pct_of_basic)), 2)


@dataclass
class AnnualTdsBreakdown:
    gross_annual: float
    standard_deduction: float
    hra_exemption_amount: float
    chapter_via_deductions: float
    taxable_income: float
    annual_tax: float
    monthly_tds: float


def estimate_annual_tds(
    basic_monthly: float,
    hra_monthly: float,
    special_allowance_monthly: float,
    other_allowance_monthly: float,
    regime: str,
    is_metro: bool = False,
    section_80c: float = 0.0,
    section_80d: float = 0.0,
    home_loan_interest: float = 0.0,
    rent_paid_monthly: float = 0.0,
) -> AnnualTdsBreakdown:
    basic_annual = basic_monthly * 12
    hra_annual = hra_monthly * 12
    gross_annual = (basic_monthly + hra_monthly + special_allowance_monthly + other_allowance_monthly) * 12

    if regime == "old":
        standard_deduction = STANDARD_DEDUCTION_OLD
        hra_exempt = hra_exemption(basic_annual, hra_annual, rent_paid_monthly * 12, is_metro)
        chapter_via = min(section_80c, SECTION_80C_CAP) + min(section_80d, SECTION_80D_CAP) + min(home_loan_interest, HOME_LOAN_INTEREST_CAP)
    else:
        standard_deduction = STANDARD_DEDUCTION_NEW
        hra_exempt = 0.0
        chapter_via = 0.0

    taxable_income = max(0.0, gross_annual - standard_deduction - hra_exempt - chapter_via)
    annual_tax = compute_annual_tax(taxable_income, regime)

    return AnnualTdsBreakdown(
        gross_annual=round(gross_annual, 2),
        standard_deduction=standard_deduction,
        hra_exemption_amount=hra_exempt,
        chapter_via_deductions=round(chapter_via, 2),
        taxable_income=round(taxable_income, 2),
        annual_tax=annual_tax,
        monthly_tds=round(annual_tax / 12, 2),
    )
