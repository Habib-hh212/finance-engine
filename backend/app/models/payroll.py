import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaxRegime:
    OLD = "old"
    NEW = "new"


TAX_REGIMES = {TaxRegime.OLD, TaxRegime.NEW}


class PayrollRunStatus:
    POSTED = "posted"


class Employee(Base):
    """An employee on this company's payroll -- distinct from Vendor/Customer
    since salary isn't an AP bill, it's computed fresh every run from a flat
    CTC breakup (Basic/HRA/Special Allowance/Other) and put through Section
    192 slab-based TDS rather than a fixed vendor TDS rate. tax_regime picks
    which slab table and which deductions apply in payroll_tax.py -- an
    employee can switch regimes at the start of a financial year, same as
    real Indian payroll."""

    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tax_regime: Mapped[str] = mapped_column(String(10), nullable=False, default=TaxRegime.NEW)
    basic_monthly: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    hra_monthly: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    special_allowance_monthly: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    other_allowance_monthly: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    is_metro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class InvestmentDeclaration(Base):
    """An employee's declared tax-saving investments for one financial year
    (India's FY runs April-March, stored as the starting year e.g. 2026 for
    FY 2026-27) -- only relevant under the old regime, which is the only one
    that still allows Chapter VI-A deductions and HRA exemption. The new
    regime ignores this row entirely (see payroll_tax.estimate_annual_tds)."""

    __tablename__ = "investment_declarations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    financial_year: Mapped[int] = mapped_column(Integer, nullable=False)
    section_80c: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    section_80d: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    home_loan_interest: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    rent_paid_monthly: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)


class PayrollRun(Base):
    """One month's payroll cycle for a company. period_month/period_year
    identify the salary month being paid (not the payment date); a company
    can only run payroll once per period -- see payroll.run_payroll's
    duplicate-period check. journal_entry_id points at the single balanced
    entry this run posts (salary expense + employer contributions on the
    debit side, all statutory payables and net cash paid on the credit
    side), same one-entry-per-transaction convention AR/AP invoices use."""

    __tablename__ = "payroll_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PayrollRunStatus.POSTED)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)


class Payslip(Base):
    """One employee's computed pay for one PayrollRun -- the gross/deduction/
    net breakdown is stored here (rather than recomputed on read) so a
    payslip PDF or Form 16 always reflects exactly what was posted to the
    ledger that month, even if the employee's salary or tax regime changes
    later."""

    __tablename__ = "payslips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payroll_runs.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    basic: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    hra: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    special_allowance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    other_allowance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    gross_pay: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    pf_employee: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    pf_employer: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    esi_employee: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    esi_employer: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    professional_tax: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    tds_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    net_pay: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
