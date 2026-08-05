import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access, require_resource_company_access
from app.database import get_db
from app.models import Scenario, User
from app.schemas.scenario import ScenarioCreate, ScenarioForecastOut, ScenarioOut
from app.schemas.statement_forecast import BalanceSheetForecastPeriodOut, IncomeStatementForecastPeriodOut
from app.services import audit, statement_forecast

router = APIRouter(tags=["scenarios"])


@router.post("/scenarios", response_model=ScenarioOut)
def create_scenario( payload: ScenarioCreate,
    company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    scenario = Scenario(company_id=company_id, **payload.model_dump())
    db.add(scenario)
    db.flush()
    audit.record(db, company_id, "scenario", scenario.id, "create", current_user, f"Created scenario '{scenario.name}'")
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/scenarios", response_model=list[ScenarioOut])
def list_scenarios(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    return db.query(Scenario).filter(Scenario.company_id == company_id).all()


@router.delete("/scenarios/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    require_resource_company_access(db, current_user, scenario.company_id)
    audit.record(db, scenario.company_id, "scenario", scenario.id, "delete", current_user, f"Deleted scenario '{scenario.name}'")
    db.delete(scenario)
    db.commit()


@router.get("/scenarios/{scenario_id}/forecast", response_model=ScenarioForecastOut)
def get_scenario_forecast(
    scenario_id: uuid.UUID,
    start_period: date,
    periods: int = Query(12, ge=1, le=36),
    dso_days: float = 45,
    dpo_days: float = 30,
    collection_lag_days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    require_resource_company_access(db, current_user, scenario.company_id)

    company_id = scenario.company_id
    base_income = statement_forecast.forecast_income_statement(db, company_id, start_period, periods)
    scenario_income = statement_forecast.forecast_income_statement(
        db,
        company_id,
        start_period,
        periods,
        sales_growth_pct=float(scenario.sales_growth_pct),
        expense_growth_pct=float(scenario.expense_growth_pct),
    )
    base_balance = statement_forecast.forecast_balance_sheet(
        db, company_id, start_period, periods, dso_days=dso_days, dpo_days=dpo_days, collection_lag_days=collection_lag_days
    )
    scenario_balance = statement_forecast.forecast_balance_sheet(
        db,
        company_id,
        start_period,
        periods,
        dso_days=dso_days,
        dpo_days=dpo_days,
        collection_lag_days=collection_lag_days,
        sales_growth_pct=float(scenario.sales_growth_pct),
        expense_growth_pct=float(scenario.expense_growth_pct),
    )

    return ScenarioForecastOut(
        scenario=scenario,
        base_income_statement=[IncomeStatementForecastPeriodOut(**row.__dict__) for row in base_income],
        scenario_income_statement=[IncomeStatementForecastPeriodOut(**row.__dict__) for row in scenario_income],
        base_balance_sheet=[BalanceSheetForecastPeriodOut(**row.__dict__) for row in base_balance],
        scenario_balance_sheet=[BalanceSheetForecastPeriodOut(**row.__dict__) for row in scenario_balance],
    )
