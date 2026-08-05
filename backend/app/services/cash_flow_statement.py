"""The Cash Flow *Statement* -- not to be confused with the forward-looking
Cash Flow *Forecast* elsewhere in this app. This is the classic indirect-
method historical statement, built entirely from what's already posted:

  Operating = net income + depreciation (non-cash, added back)
              - increase in Accounts Receivable (cash tied up in unpaid sales)
              + increase in Accounts Payable (cash kept by not yet paying bills)
  Investing = asset disposal proceeds - asset acquisitions, from the Fixed
              Assets module
  Financing = 0, always -- this system has no loan or equity-transaction
              model, so rather than fabricate a number, financing activity
              is reported as untracked. Documented here, not hidden.

The statement proves itself the same way the Balance Sheet does: opening
cash balance + the net change this computes should equal the actual
closing cash balance from the ledger. If it doesn't, something upstream
(an uncategorized account, a manual actuals-post that bypassed a real
transaction) is inconsistent -- `is_proven` surfaces that instead of
assuming it's fine.
"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import ActualLine, Asset, DepreciationEntry, GLAccount
from app.models.fixed_asset import DISPOSED_STATUSES
from app.services.financial_statements import income_statement

TOLERANCE = 0.01


def _cash_gl_account_ids(db: Session, company_id) -> list:
    return [a.id for a in db.query(GLAccount).filter(GLAccount.company_id == company_id, GLAccount.forecast_role == "cash").all()]


def _balance_change(db: Session, company_id, forecast_role: str, start: date, end: date) -> float:
    account_ids = [a.id for a in db.query(GLAccount).filter(GLAccount.company_id == company_id, GLAccount.forecast_role == forecast_role).all()]
    if not account_ids:
        return 0.0
    opening = sum(
        float(line.amount)
        for line in db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id.in_(account_ids), ActualLine.period < start)
    )
    closing = sum(
        float(line.amount)
        for line in db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id.in_(account_ids), ActualLine.period <= end)
    )
    return round(closing - opening, 2)


def _cash_balance(db: Session, company_id, cash_account_ids: list, before: date) -> float:
    if not cash_account_ids:
        return 0.0
    return round(
        sum(
            float(line.amount)
            for line in db.query(ActualLine).filter(
                ActualLine.company_id == company_id, ActualLine.gl_account_id.in_(cash_account_ids), ActualLine.period < before
            )
        ),
        2,
    )


@dataclass
class CashFlowStatement:
    start: date
    end: date
    net_income: float
    depreciation_add_back: float
    increase_in_receivables: float
    increase_in_payables: float
    net_operating_cash_flow: float
    asset_acquisitions: float
    disposal_proceeds: float
    net_investing_cash_flow: float
    net_financing_cash_flow: float
    net_change_in_cash: float
    opening_cash_balance: float
    closing_cash_balance: float
    is_proven: bool


def cash_flow_statement(db: Session, company_id, start: date, end: date) -> CashFlowStatement:
    stmt = income_statement(db, company_id, start, end)

    depreciation = round(
        sum(
            float(row.depreciation_amount)
            for row in db.query(DepreciationEntry)
            .join(Asset, Asset.id == DepreciationEntry.asset_id)
            .filter(Asset.company_id == company_id, DepreciationEntry.period >= start, DepreciationEntry.period <= end)
            .all()
        ),
        2,
    )

    increase_in_ar = _balance_change(db, company_id, "accounts_receivable", start, end)
    increase_in_ap = _balance_change(db, company_id, "accounts_payable", start, end)
    operating = round(stmt.net_profit + depreciation - increase_in_ar + increase_in_ap, 2)

    acquisitions = round(
        sum(
            float(a.capitalized_cost)
            for a in db.query(Asset).filter(Asset.company_id == company_id, Asset.acquisition_date >= start, Asset.acquisition_date <= end).all()
        ),
        2,
    )
    proceeds = round(
        sum(
            float(a.disposal_proceeds or 0)
            for a in db.query(Asset)
            .filter(
                Asset.company_id == company_id,
                Asset.status.in_(DISPOSED_STATUSES),
                Asset.disposal_date.isnot(None),
                Asset.disposal_date >= start,
                Asset.disposal_date <= end,
            )
            .all()
        ),
        2,
    )
    investing = round(proceeds - acquisitions, 2)
    financing = 0.0
    net_change = round(operating + investing + financing, 2)

    cash_ids = _cash_gl_account_ids(db, company_id)
    opening_cash = _cash_balance(db, company_id, cash_ids, start)
    closing_cash = round(opening_cash + sum(
        float(line.amount)
        for line in db.query(ActualLine).filter(ActualLine.company_id == company_id, ActualLine.gl_account_id.in_(cash_ids), ActualLine.period >= start, ActualLine.period <= end)
    ), 2) if cash_ids else 0.0

    return CashFlowStatement(
        start=start,
        end=end,
        net_income=stmt.net_profit,
        depreciation_add_back=depreciation,
        increase_in_receivables=increase_in_ar,
        increase_in_payables=increase_in_ap,
        net_operating_cash_flow=operating,
        asset_acquisitions=acquisitions,
        disposal_proceeds=proceeds,
        net_investing_cash_flow=investing,
        net_financing_cash_flow=financing,
        net_change_in_cash=net_change,
        opening_cash_balance=opening_cash,
        closing_cash_balance=closing_cash,
        is_proven=abs(round((opening_cash + net_change) - closing_cash, 2)) <= TOLERANCE,
    )
