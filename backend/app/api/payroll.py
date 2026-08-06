import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import Company, Employee, InvestmentDeclaration, PayrollRun, Payslip, User
from app.schemas.payroll import (
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    Form16SummaryOut,
    InvestmentDeclarationCreate,
    InvestmentDeclarationOut,
    PayrollRunCreate,
    PayrollRunOut,
    PayslipOut,
)
from app.services import audit, payroll_documents
from app.services import payroll as payroll_service

router = APIRouter(tags=["payroll"])


def _get_employee_or_404(db: Session, employee_id: uuid.UUID, company_id: uuid.UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None or employee.company_id != company_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("/employees", response_model=EmployeeOut)
def create_employee(
    payload: EmployeeCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if payload.basic_monthly <= 0:
        raise HTTPException(status_code=422, detail="basic_monthly must be positive.")
    employee = Employee(company_id=company_id, **payload.model_dump())
    db.add(employee)
    db.flush()
    audit.record(db, company_id, "employee", employee.id, "create", current_user, f"Added employee {employee.name}")
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(Employee).filter(Employee.company_id == company_id).order_by(Employee.name).all()


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = _get_employee_or_404(db, employee_id, company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.flush()
    audit.record(db, company_id, "employee", employee.id, "update", current_user, f"Updated employee {employee.name}")
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/employees/{employee_id}/investment-declarations", response_model=InvestmentDeclarationOut)
def upsert_investment_declaration(
    employee_id: uuid.UUID,
    payload: InvestmentDeclarationCreate,
    company_id: uuid.UUID = Depends(require_company_access),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = _get_employee_or_404(db, employee_id, company_id)
    declaration = (
        db.query(InvestmentDeclaration)
        .filter(InvestmentDeclaration.employee_id == employee.id, InvestmentDeclaration.financial_year == payload.financial_year)
        .first()
    )
    if declaration is None:
        declaration = InvestmentDeclaration(employee_id=employee.id, **payload.model_dump())
        db.add(declaration)
    else:
        for field, value in payload.model_dump(exclude={"financial_year"}).items():
            setattr(declaration, field, value)
    db.flush()
    audit.record(db, company_id, "investment_declaration", declaration.id, "upsert", current_user, f"Investment declaration for {employee.name}, FY{payload.financial_year}")
    db.commit()
    db.refresh(declaration)
    return declaration


@router.get("/employees/{employee_id}/investment-declarations", response_model=list[InvestmentDeclarationOut])
def list_investment_declarations(employee_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, employee_id, company_id)
    return (
        db.query(InvestmentDeclaration)
        .filter(InvestmentDeclaration.employee_id == employee.id)
        .order_by(InvestmentDeclaration.financial_year.desc())
        .all()
    )


def _run_out(db: Session, run) -> PayrollRunOut:
    payslips = db.query(Payslip).filter(Payslip.payroll_run_id == run.id).all()
    return PayrollRunOut(
        id=run.id,
        period_month=run.period_month,
        period_year=run.period_year,
        run_date=run.run_date,
        status=run.status,
        journal_entry_id=run.journal_entry_id,
        payslips=[PayslipOut.model_validate(p) for p in payslips],
    )


@router.post("/payroll-runs", response_model=PayrollRunOut)
def create_payroll_run(
    payload: PayrollRunCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        run = payroll_service.run_payroll(
            db,
            company_id,
            payload.period_month,
            payload.period_year,
            payload.cash_gl_account_id,
            payload.run_date,
        )
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    audit.record(db, company_id, "payroll_run", run.id, "create", current_user, f"Ran payroll for {payload.period_month}/{payload.period_year}")
    db.commit()
    return _run_out(db, run)


@router.get("/payroll-runs", response_model=list[PayrollRunOut])
def list_payroll_runs(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    runs = db.query(PayrollRun).filter(PayrollRun.company_id == company_id).order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc()).all()
    return [_run_out(db, run) for run in runs]


@router.get("/payslips/{payslip_id}/pdf")
def get_payslip_pdf(payslip_id: uuid.UUID, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    payslip = db.get(Payslip, payslip_id)
    if payslip is None:
        raise HTTPException(status_code=404, detail="Payslip not found")
    run = db.get(PayrollRun, payslip.payroll_run_id)
    if run is None or run.company_id != company_id:
        raise HTTPException(status_code=404, detail="Payslip not found")
    employee = db.get(Employee, payslip.employee_id)
    company = db.get(Company, company_id)
    pdf_bytes = payroll_documents.render_payslip_pdf(company, employee, payslip, run.period_month, run.period_year)
    filename = f"payslip-{employee.name.replace(' ', '-')}-{run.period_month}-{run.period_year}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/employees/{employee_id}/form16/pdf")
def get_form16_pdf(employee_id: uuid.UUID, financial_year: int = Query(...), company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    try:
        summary = payroll_service.generate_form16(db, company_id, employee_id, financial_year)
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    company = db.get(Company, company_id)
    pdf_bytes = payroll_documents.render_form16_pdf(company, summary)
    filename = f"form16-{summary.employee.name.replace(' ', '-')}-FY{financial_year}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/employees/{employee_id}/form16", response_model=Form16SummaryOut)
def get_form16_summary(employee_id: uuid.UUID, financial_year: int = Query(...), company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    try:
        summary = payroll_service.generate_form16(db, company_id, employee_id, financial_year)
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Form16SummaryOut(
        employee_id=summary.employee.id,
        financial_year=summary.financial_year,
        regime=summary.regime,
        total_gross=summary.total_gross,
        total_tds=summary.total_tds,
        months=[{"period_month": m.period_month, "period_year": m.period_year, "gross_pay": m.gross_pay, "tds_amount": m.tds_amount} for m in summary.months],
    )
