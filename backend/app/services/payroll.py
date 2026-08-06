"""Monthly payroll: for every active employee, compute gross pay, employer
and employee Provident Fund, ESI (only below the wage threshold), a
simplified Professional Tax slab, and Section 192 TDS (via payroll_tax.py),
then post one balanced journal entry for the whole run -- salary expense
and the employer's own PF/ESI contribution on the debit side, every
statutory payable plus the net cash actually paid out on the credit side.
Net pay is disbursed from the given cash account in the same entry (no
separate "Salary Payable then pay it" step, unlike AP bills) since payroll
is normally run and paid same-day.

PF/ESI/Professional Tax below are simplified, generic rules -- real rates
vary by state (Professional Tax) and have wage ceilings (EPF's mandatory
contribution caps at a 15,000/month basic in practice); see payroll_tax.py
for the same caveat on the TDS side.
"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import Employee, GLAccount, InvestmentDeclaration, JournalEntry, PayrollRun, Payslip
from app.services import bookkeeping, payroll_tax

PF_RATE = 0.12
ESI_WAGE_CEILING = 21_000.0
ESI_EMPLOYEE_RATE = 0.0075
ESI_EMPLOYER_RATE = 0.0325
PROFESSIONAL_TAX_THRESHOLD = 15_000.0
PROFESSIONAL_TAX_AMOUNT = 200.0


class PayrollError(ValueError):
    """Raised when a payroll run can't be processed."""


def financial_year_for_period(period_month: int, period_year: int) -> int:
    """India's FY runs April-March; a period in Jan-Mar belongs to the FY
    that started the previous April. Returned as the FY's starting year."""
    return period_year if period_month >= 4 else period_year - 1


def _control_account(db: Session, company_id, forecast_role: str, label: str) -> GLAccount:
    account = db.query(GLAccount).filter(GLAccount.company_id == company_id, GLAccount.forecast_role == forecast_role).first()
    if account is None:
        raise PayrollError(f"No G/L account is tagged as {label} for this company -- tag one on the Chart of Accounts page.")
    return account


def _professional_tax(gross_monthly: float) -> float:
    return PROFESSIONAL_TAX_AMOUNT if gross_monthly > PROFESSIONAL_TAX_THRESHOLD else 0.0


@dataclass
class PayslipCalc:
    employee: Employee
    basic: float
    hra: float
    special_allowance: float
    other_allowance: float
    gross_pay: float
    pf_employee: float
    pf_employer: float
    esi_employee: float
    esi_employer: float
    professional_tax: float
    tds_amount: float
    net_pay: float


def compute_payslip(db: Session, employee: Employee, period_month: int, period_year: int) -> PayslipCalc:
    fy = financial_year_for_period(period_month, period_year)
    declaration = (
        db.query(InvestmentDeclaration)
        .filter(InvestmentDeclaration.employee_id == employee.id, InvestmentDeclaration.financial_year == fy)
        .first()
    )

    basic = float(employee.basic_monthly)
    hra = float(employee.hra_monthly)
    special = float(employee.special_allowance_monthly)
    other = float(employee.other_allowance_monthly)
    gross = round(basic + hra + special + other, 2)

    breakdown = payroll_tax.estimate_annual_tds(
        basic_monthly=basic,
        hra_monthly=hra,
        special_allowance_monthly=special,
        other_allowance_monthly=other,
        regime=employee.tax_regime,
        is_metro=employee.is_metro,
        section_80c=float(declaration.section_80c) if declaration else 0.0,
        section_80d=float(declaration.section_80d) if declaration else 0.0,
        home_loan_interest=float(declaration.home_loan_interest) if declaration else 0.0,
        rent_paid_monthly=float(declaration.rent_paid_monthly) if declaration else 0.0,
    )

    pf_employee = round(basic * PF_RATE, 2)
    pf_employer = round(basic * PF_RATE, 2)
    if gross <= ESI_WAGE_CEILING:
        esi_employee = round(gross * ESI_EMPLOYEE_RATE, 2)
        esi_employer = round(gross * ESI_EMPLOYER_RATE, 2)
    else:
        esi_employee = esi_employer = 0.0
    pt = _professional_tax(gross)
    tds = breakdown.monthly_tds

    net_pay = round(gross - pf_employee - esi_employee - pt - tds, 2)

    return PayslipCalc(
        employee=employee,
        basic=basic,
        hra=hra,
        special_allowance=special,
        other_allowance=other,
        gross_pay=gross,
        pf_employee=pf_employee,
        pf_employer=pf_employer,
        esi_employee=esi_employee,
        esi_employer=esi_employer,
        professional_tax=pt,
        tds_amount=tds,
        net_pay=net_pay,
    )


def run_payroll(db: Session, company_id, period_month: int, period_year: int, cash_gl_account_id, run_date: date, currency: str = "USD") -> PayrollRun:
    if not (1 <= period_month <= 12):
        raise PayrollError("period_month must be between 1 and 12.")

    existing = (
        db.query(PayrollRun)
        .filter(PayrollRun.company_id == company_id, PayrollRun.period_month == period_month, PayrollRun.period_year == period_year)
        .first()
    )
    if existing is not None:
        raise PayrollError(f"Payroll for {period_month}/{period_year} has already been run.")

    employees = db.query(Employee).filter(Employee.company_id == company_id, Employee.is_active.is_(True)).all()
    if not employees:
        raise PayrollError("This company has no active employees.")

    calcs = [compute_payslip(db, employee, period_month, period_year) for employee in employees]

    total_gross = round(sum(c.gross_pay for c in calcs), 2)
    total_pf_employee = round(sum(c.pf_employee for c in calcs), 2)
    total_pf_employer = round(sum(c.pf_employer for c in calcs), 2)
    total_esi_employee = round(sum(c.esi_employee for c in calcs), 2)
    total_esi_employer = round(sum(c.esi_employer for c in calcs), 2)
    total_pt = round(sum(c.professional_tax for c in calcs), 2)
    total_tds = round(sum(c.tds_amount for c in calcs), 2)
    total_net = round(sum(c.net_pay for c in calcs), 2)

    salary_expense_account = _control_account(db, company_id, "salary_expense", "Salary Expense")
    pf_payable_account = _control_account(db, company_id, "pf_payable", "PF Payable")

    lines = [
        bookkeeping.LineInput(
            gl_account_id=salary_expense_account.id,
            debit_amount=round(total_gross + total_pf_employer + total_esi_employer, 2),
            description=f"Salary expense {period_month}/{period_year}",
        ),
        bookkeeping.LineInput(gl_account_id=pf_payable_account.id, credit_amount=round(total_pf_employee + total_pf_employer, 2)),
        bookkeeping.LineInput(gl_account_id=cash_gl_account_id, credit_amount=total_net, description="Net salaries paid"),
    ]
    if total_esi_employee + total_esi_employer > 0:
        esi_account = _control_account(db, company_id, "esi_payable", "ESI Payable")
        lines.append(bookkeeping.LineInput(gl_account_id=esi_account.id, credit_amount=round(total_esi_employee + total_esi_employer, 2)))
    if total_pt > 0:
        pt_account = _control_account(db, company_id, "professional_tax_payable", "Professional Tax Payable")
        lines.append(bookkeeping.LineInput(gl_account_id=pt_account.id, credit_amount=total_pt))
    if total_tds > 0:
        tds_account = _control_account(db, company_id, "tds_payable", "TDS Payable")
        lines.append(bookkeeping.LineInput(gl_account_id=tds_account.id, credit_amount=total_tds))

    entry: JournalEntry = bookkeeping.create_journal_entry(
        db,
        company_id,
        run_date,
        lines,
        reference=f"Payroll {period_month}/{period_year}",
        description=f"Payroll run for {period_month}/{period_year} ({len(employees)} employees)",
        currency=currency,
    )
    entry = bookkeeping.post_journal_entry(db, entry)

    run = PayrollRun(
        company_id=company_id,
        period_month=period_month,
        period_year=period_year,
        run_date=run_date,
        journal_entry_id=entry.id,
    )
    db.add(run)
    db.flush()

    for calc in calcs:
        db.add(
            Payslip(
                payroll_run_id=run.id,
                employee_id=calc.employee.id,
                basic=calc.basic,
                hra=calc.hra,
                special_allowance=calc.special_allowance,
                other_allowance=calc.other_allowance,
                gross_pay=calc.gross_pay,
                pf_employee=calc.pf_employee,
                pf_employer=calc.pf_employer,
                esi_employee=calc.esi_employee,
                esi_employer=calc.esi_employer,
                professional_tax=calc.professional_tax,
                tds_amount=calc.tds_amount,
                net_pay=calc.net_pay,
            )
        )

    db.commit()
    db.refresh(run)
    return run


@dataclass
class Form16MonthRow:
    period_month: int
    period_year: int
    gross_pay: float
    tds_amount: float


@dataclass
class Form16Summary:
    employee: Employee
    financial_year: int
    regime: str
    total_gross: float
    total_tds: float
    months: list


def generate_form16(db: Session, company_id, employee_id, financial_year: int) -> Form16Summary:
    employee = db.get(Employee, employee_id)
    if employee is None or employee.company_id != company_id:
        raise PayrollError("Employee not found in this company.")

    rows = (
        db.query(Payslip, PayrollRun)
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)
        .filter(
            Payslip.employee_id == employee_id,
            PayrollRun.company_id == company_id,
        )
        .all()
    )

    months = [
        Form16MonthRow(period_month=run.period_month, period_year=run.period_year, gross_pay=float(slip.gross_pay), tds_amount=float(slip.tds_amount))
        for slip, run in rows
        if financial_year_for_period(run.period_month, run.period_year) == financial_year
    ]
    months.sort(key=lambda m: (m.period_year, m.period_month))

    return Form16Summary(
        employee=employee,
        financial_year=financial_year,
        regime=employee.tax_regime,
        total_gross=round(sum(m.gross_pay for m in months), 2),
        total_tds=round(sum(m.tds_amount for m in months), 2),
        months=months,
    )
