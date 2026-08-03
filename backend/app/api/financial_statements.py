import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.financial_statements import AccountAmountOut, BalanceSheetOut, IncomeStatementOut
from app.services import financial_statements

router = APIRouter(prefix="/reports", tags=["financial-statements"])


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
