import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth import require_company_access
from app.database import get_db
from app.models import GLAccount, JournalEntry, JournalEntryLine
from app.models.journal_entry import JournalEntryStatus
from app.schemas.financial_statements import (
    AccountAmountOut,
    BalanceSheetOut,
    CashFlowStatementOut,
    IncomeStatementOut,
    IncomeStatementTrendPointOut,
    StatementUploadResult,
)
from app.services import bookkeeping, cash_flow_statement, financial_statements, report_generation, statement_import
from app.services.excel_export import sheets_to_xlsx_response

router = APIRouter(prefix="/reports", tags=["financial-statements"])


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "report"


@router.post("/upload-statements", response_model=StatementUploadResult)
async def upload_statements(file: UploadFile, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, or .csv files are supported")
    contents = await file.read()
    try:
        result = statement_import.import_statement_file(db, company_id, contents, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.get("/income-statement", response_model=IncomeStatementOut)
def get_income_statement(
    company_id: uuid.UUID = Depends(require_company_access),
    start_period: date = Query(..., description="First day of the first month, e.g. 2026-01-01"),
    end_period: date = Query(..., description="First day of the last month, e.g. 2026-12-01"),
    db: Session = Depends(get_db)):
    result = financial_statements.income_statement(db, company_id, start_period, end_period)
    return IncomeStatementOut(
        start_period=result.start_period,
        end_period=result.end_period,
        revenue_lines=[AccountAmountOut(**line.__dict__) for line in result.revenue_lines],
        total_revenue=result.total_revenue,
        expense_lines=[AccountAmountOut(**line.__dict__) for line in result.expense_lines],
        total_expense=result.total_expense,
        net_profit=result.net_profit,
    )


@router.get("/balance-sheet", response_model=BalanceSheetOut)
def get_balance_sheet(company_id: uuid.UUID = Depends(require_company_access), as_of: date = Query(...), db: Session = Depends(get_db)):
    result = financial_statements.balance_sheet(db, company_id, as_of)
    return BalanceSheetOut(
        as_of=result.as_of,
        asset_lines=[AccountAmountOut(**line.__dict__) for line in result.asset_lines],
        total_assets=result.total_assets,
        liability_lines=[AccountAmountOut(**line.__dict__) for line in result.liability_lines],
        total_liabilities=result.total_liabilities,
        equity_lines=[AccountAmountOut(**line.__dict__) for line in result.equity_lines],
        total_equity=result.total_equity,
        is_balanced=result.is_balanced,
        difference=result.difference,
    )


@router.get("/cash-flow-statement", response_model=CashFlowStatementOut)
def get_cash_flow_statement(company_id: uuid.UUID = Depends(require_company_access), start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    result = cash_flow_statement.cash_flow_statement(db, company_id, start, end)
    return CashFlowStatementOut(**result.__dict__)


@router.get("/income-statement/trend", response_model=list[IncomeStatementTrendPointOut])
def get_income_statement_trend(
    company_id: uuid.UUID = Depends(require_company_access),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db)):
    rows = financial_statements.income_statement_trend(db, company_id, start_period, end_period)
    return [IncomeStatementTrendPointOut(**row.__dict__) for row in rows]


@router.get("/income-statement/export")
def export_income_statement(
    company_id: uuid.UUID = Depends(require_company_access),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db)):
    result = financial_statements.income_statement(db, company_id, start_period, end_period)
    revenue_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in result.revenue_lines]
    revenue_rows.append({"Code": "", "Account": "Total Revenue", "Amount": result.total_revenue})
    expense_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in result.expense_lines]
    expense_rows.append({"Code": "", "Account": "Total Expense", "Amount": result.total_expense})
    expense_rows.append({"Code": "", "Account": "Net Profit", "Amount": result.net_profit})
    return sheets_to_xlsx_response(
        {"Revenue": revenue_rows, "Expenses": expense_rows},
        f"income-statement-{start_period}-to-{end_period}.xlsx",
    )


@router.get("/balance-sheet/export")
def export_balance_sheet(company_id: uuid.UUID = Depends(require_company_access), as_of: date = Query(...), db: Session = Depends(get_db)):
    result = financial_statements.balance_sheet(db, company_id, as_of)
    asset_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in result.asset_lines]
    asset_rows.append({"Code": "", "Account": "Total Assets", "Amount": result.total_assets})
    liability_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in result.liability_lines]
    liability_rows.append({"Code": "", "Account": "Total Liabilities", "Amount": result.total_liabilities})
    equity_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in result.equity_lines]
    equity_rows.append({"Code": "", "Account": "Total Equity", "Amount": result.total_equity})
    return sheets_to_xlsx_response(
        {"Assets": asset_rows, "Liabilities": liability_rows, "Equity": equity_rows},
        f"balance-sheet-{as_of}.xlsx",
    )


@router.get("/books/export")
def export_all_books(
    company_id: uuid.UUID = Depends(require_company_access),
    start: date = Query(..., description="First day of the journal/statement period"),
    end: date = Query(..., description="Last day of the journal/statement period"),
    db: Session = Depends(get_db)):
    """Every book at once: the Journal (every posted entry in the range),
    the Trial Balance and Balance Sheet as of the end date, and the Income
    Statement for the range -- one workbook instead of four separate
    downloads."""
    accounts = {a.id: a for a in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    entries = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalEntryStatus.POSTED,
            JournalEntry.entry_date >= start,
            JournalEntry.entry_date <= end,
        )
        .order_by(JournalEntry.entry_date, JournalEntry.created_at)
        .all()
    )
    journal_rows = []
    if entries:
        lines = db.query(JournalEntryLine).filter(JournalEntryLine.journal_entry_id.in_([e.id for e in entries])).all()
        lines_by_entry: dict = {}
        for line in lines:
            lines_by_entry.setdefault(line.journal_entry_id, []).append(line)
        for entry in entries:
            for line in lines_by_entry.get(entry.id, []):
                account = accounts.get(line.gl_account_id)
                journal_rows.append(
                    {
                        "Date": entry.entry_date,
                        "Reference": entry.reference or "",
                        "Account Code": account.code if account else "?",
                        "Account Name": account.name if account else "?",
                        "Debit": float(line.debit_amount),
                        "Credit": float(line.credit_amount),
                        "Description": line.description or "",
                    }
                )

    tb_rows = bookkeeping.trial_balance(db, company_id, end)
    trial_balance_rows = [
        {"Code": r.gl_account_code, "Account": r.gl_account_name, "Category": r.category, "Total Debit": r.total_debit, "Total Credit": r.total_credit, "Net Balance": r.net_balance}
        for r in tb_rows
    ]

    stmt = financial_statements.income_statement(db, company_id, start, end)
    income_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in stmt.revenue_lines]
    income_rows.append({"Code": "", "Account": "Total Revenue", "Amount": stmt.total_revenue})
    income_rows += [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in stmt.expense_lines]
    income_rows.append({"Code": "", "Account": "Total Expense", "Amount": stmt.total_expense})
    income_rows.append({"Code": "", "Account": "Net Profit", "Amount": stmt.net_profit})

    bs = financial_statements.balance_sheet(db, company_id, end)
    balance_rows = [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in bs.asset_lines]
    balance_rows.append({"Code": "", "Account": "Total Assets", "Amount": bs.total_assets})
    balance_rows += [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in bs.liability_lines]
    balance_rows.append({"Code": "", "Account": "Total Liabilities", "Amount": bs.total_liabilities})
    balance_rows += [{"Code": line.code, "Account": line.name, "Amount": line.amount} for line in bs.equity_lines]
    balance_rows.append({"Code": "", "Account": "Total Equity", "Amount": bs.total_equity})

    return sheets_to_xlsx_response(
        {
            "Journal": journal_rows,
            "Trial Balance": trial_balance_rows,
            "Income Statement": income_rows,
            "Balance Sheet": balance_rows,
        },
        f"books-{start}-to-{end}.xlsx",
    )


@router.get("/board-report/pdf")
def get_board_report_pdf(
    company_id: uuid.UUID = Depends(require_company_access),
    start_period: date = Query(...),
    end_period: date = Query(...),
    as_of: date = Query(...),
    db: Session = Depends(get_db)):
    data = report_generation.build_report_data(db, company_id, start_period, end_period, as_of)
    pdf_bytes = report_generation.render_pdf(data)
    filename = f"{_safe_filename(data.company_name)}-financial-report.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/board-report/pptx")
def get_board_report_pptx(
    company_id: uuid.UUID = Depends(require_company_access),
    start_period: date = Query(...),
    end_period: date = Query(...),
    as_of: date = Query(...),
    db: Session = Depends(get_db)):
    data = report_generation.build_report_data(db, company_id, start_period, end_period, as_of)
    pptx_bytes = report_generation.render_pptx(data)
    filename = f"{_safe_filename(data.company_name)}-financial-report.pptx"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
