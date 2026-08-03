import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.financial_statements import (
    AccountAmountOut,
    BalanceSheetOut,
    IncomeStatementOut,
    IncomeStatementTrendPointOut,
    StatementUploadResult,
)
from app.services import financial_statements, statement_import
from app.services.excel_export import sheets_to_xlsx_response

router = APIRouter(prefix="/reports", tags=["financial-statements"])


@router.post("/upload-statements", response_model=StatementUploadResult)
async def upload_statements(company_id: uuid.UUID, file: UploadFile, db: Session = Depends(get_db)):
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
    company_id: uuid.UUID,
    start_period: date = Query(..., description="First day of the first month, e.g. 2026-01-01"),
    end_period: date = Query(..., description="First day of the last month, e.g. 2026-12-01"),
    db: Session = Depends(get_db),
):
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
def get_balance_sheet(company_id: uuid.UUID, as_of: date = Query(...), db: Session = Depends(get_db)):
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


@router.get("/income-statement/trend", response_model=list[IncomeStatementTrendPointOut])
def get_income_statement_trend(
    company_id: uuid.UUID,
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
):
    rows = financial_statements.income_statement_trend(db, company_id, start_period, end_period)
    return [IncomeStatementTrendPointOut(**row.__dict__) for row in rows]


@router.get("/income-statement/export")
def export_income_statement(
    company_id: uuid.UUID,
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
):
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
def export_balance_sheet(company_id: uuid.UUID, as_of: date = Query(...), db: Session = Depends(get_db)):
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
