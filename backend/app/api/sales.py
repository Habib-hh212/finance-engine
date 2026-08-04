import uuid
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SalesActual
from app.schemas.sales import (
    DemandForecastPointOut,
    DemandForecastResponse,
    ForecastPointOut,
    ForecastResponse,
    ModelComparisonOut,
    MonteCarloPointOut,
    MonteCarloResponse,
    SalesUploadResult,
)
from app.services import forecasting, monte_carlo
from app.services.excel_export import sheets_to_xlsx_response
from app.services.sales_import import import_sales_file

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/upload", response_model=SalesUploadResult)
async def upload_sales_csv(company_id: uuid.UUID, file: UploadFile, db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, or .xls files are supported")
    contents = await file.read()
    try:
        result = import_sales_file(db, company_id, contents, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


def _sales_history(db: Session, company_id: uuid.UUID, product_id: uuid.UUID) -> list[SalesActual]:
    return (
        db.query(SalesActual)
        .filter(SalesActual.company_id == company_id, SalesActual.product_id == product_id)
        .order_by(SalesActual.period)
        .all()
    )


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    company_id: uuid.UUID,
    product_id: uuid.UUID,
    model: str = Query(
        "exponential_smoothing",
        description="moving_average | weighted_average | exponential_smoothing | random_forest | gradient_boosting",
    ),
    periods: int = Query(3, ge=1, le=24),
    db: Session = Depends(get_db),
):
    actuals = _sales_history(db, company_id, product_id)
    if not actuals:
        raise HTTPException(status_code=404, detail="No sales history for this company/product")

    history = pd.Series(
        [float(a.amount) for a in actuals],
        index=[a.period for a in actuals],
    )
    currency = actuals[-1].currency

    try:
        points = forecasting.forecast(history, model=model, periods=periods)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    last_period: date = actuals[-1].period
    out_points = [
        ForecastPointOut(
            period=last_period + relativedelta(months=p.period_offset),
            forecast=p.forecast,
            lower_bound=p.lower_bound,
            upper_bound=p.upper_bound,
            currency=currency,
        )
        for p in points
    ]

    return ForecastResponse(
        company_id=company_id,
        product_id=product_id,
        model=model,
        history_periods=len(actuals),
        points=out_points,
    )


@router.get("/forecast/demand", response_model=DemandForecastResponse)
def get_demand_forecast(
    company_id: uuid.UUID,
    product_id: uuid.UUID,
    model: str = Query(
        "exponential_smoothing",
        description="moving_average | weighted_average | exponential_smoothing | random_forest | gradient_boosting",
    ),
    periods: int = Query(3, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """Demand prediction: the same forecast models as /sales/forecast, but
    run against units sold (quantity) instead of revenue ($) -- a genuinely
    different question (how many units to plan production/inventory for)
    that revenue forecasting doesn't answer on its own, since price mix can
    move independently of volume."""
    actuals = _sales_history(db, company_id, product_id)
    if not actuals:
        raise HTTPException(status_code=404, detail="No sales history for this company/product")

    history = pd.Series(
        [float(a.quantity) for a in actuals],
        index=[a.period for a in actuals],
    )

    try:
        points = forecasting.forecast(history, model=model, periods=periods)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    last_period: date = actuals[-1].period
    out_points = [
        DemandForecastPointOut(
            period=last_period + relativedelta(months=p.period_offset),
            forecast_units=p.forecast,
            lower_bound=p.lower_bound,
            upper_bound=p.upper_bound,
        )
        for p in points
    ]

    return DemandForecastResponse(
        company_id=company_id,
        product_id=product_id,
        model=model,
        history_periods=len(actuals),
        points=out_points,
    )


@router.get("/forecast/monte-carlo", response_model=MonteCarloResponse)
def get_monte_carlo_forecast(
    company_id: uuid.UUID,
    product_id: uuid.UUID,
    model: str = Query(
        "exponential_smoothing",
        description="moving_average | weighted_average | exponential_smoothing | random_forest | gradient_boosting",
    ),
    periods: int = Query(3, ge=1, le=24),
    trials: int = Query(1000, ge=100, le=5000),
    db: Session = Depends(get_db),
):
    """A p10/p50/p90 band per period from `trials` random simulations,
    rather than the single fixed-width confidence interval `/sales/forecast`
    returns -- see `app/services/monte_carlo.py` for why the band widens
    the further out the horizon goes."""
    actuals = _sales_history(db, company_id, product_id)
    if not actuals:
        raise HTTPException(status_code=404, detail="No sales history for this company/product")

    history = pd.Series([float(a.amount) for a in actuals], index=[a.period for a in actuals])
    currency = actuals[-1].currency

    try:
        points = monte_carlo.simulate(history, model=model, periods=periods, trials=trials)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    last_period: date = actuals[-1].period
    out_points = [
        MonteCarloPointOut(
            period=last_period + relativedelta(months=p.period_offset),
            p10=p.p10,
            p50=p.p50,
            p90=p.p90,
            mean=p.mean,
            currency=currency,
        )
        for p in points
    ]

    return MonteCarloResponse(
        company_id=company_id,
        product_id=product_id,
        model=model,
        trials=trials,
        history_periods=len(actuals),
        points=out_points,
    )


@router.get("/forecast/compare", response_model=ModelComparisonOut)
def compare_forecast_models(company_id: uuid.UUID, product_id: uuid.UUID, db: Session = Depends(get_db)):
    actuals = _sales_history(db, company_id, product_id)
    if not actuals:
        raise HTTPException(status_code=404, detail="No sales history for this company/product")

    history = pd.Series([float(a.amount) for a in actuals], index=[a.period for a in actuals])
    mape_by_model = forecasting.compare_models(history)

    return ModelComparisonOut(
        company_id=company_id,
        product_id=product_id,
        history_periods=len(actuals),
        mape_by_model=mape_by_model,
    )


@router.get("/forecast/export")
def export_forecast(
    company_id: uuid.UUID,
    product_id: uuid.UUID,
    model: str = Query("exponential_smoothing"),
    periods: int = Query(3, ge=1, le=24),
    db: Session = Depends(get_db),
):
    result = get_forecast(company_id, product_id, model, periods, db)
    rows = [
        {
            "Period": p.period,
            "Forecast": p.forecast,
            "Lower bound": p.lower_bound,
            "Upper bound": p.upper_bound,
            "Currency": p.currency,
        }
        for p in result.points
    ]
    return sheets_to_xlsx_response({"Sales Forecast": rows}, f"sales-forecast-{product_id}.xlsx")
