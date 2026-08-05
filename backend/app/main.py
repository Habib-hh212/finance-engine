import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    audit,
    auth,
    bookkeeping,
    budgets,
    cashflow,
    companies,
    controlling,
    cost_centers,
    financial_statements,
    fixed_assets,
    fx,
    insights,
    kpis,
    marginal_costing,
    products,
    profitability,
    sales,
    scenarios,
    standard_costing,
    statement_forecast,
    tax_codes,
)
from app.auth import get_current_user
from app.database import Base, engine
from app.migrations import apply_additive_columns


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_additive_columns(engine)
    yield


app = FastAPI(title="Finance Engine API", version="0.1.0", lifespan=lifespan)

# Local dev origins are always allowed; add deployed frontend origins via the
# FRONTEND_ORIGINS env var (comma-separated) once something is deployed.
default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
extra_origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins + extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

_auth_dep = [Depends(get_current_user)]
app.include_router(audit.router, dependencies=_auth_dep)
app.include_router(bookkeeping.router, dependencies=_auth_dep)
app.include_router(companies.router, dependencies=_auth_dep)
app.include_router(sales.router, dependencies=_auth_dep)
app.include_router(products.router, dependencies=_auth_dep)
app.include_router(budgets.router, dependencies=_auth_dep)
app.include_router(cashflow.router, dependencies=_auth_dep)
app.include_router(controlling.router, dependencies=_auth_dep)
app.include_router(cost_centers.router, dependencies=_auth_dep)
app.include_router(fx.router, dependencies=_auth_dep)
app.include_router(profitability.router, dependencies=_auth_dep)
app.include_router(kpis.router, dependencies=_auth_dep)
app.include_router(insights.router, dependencies=_auth_dep)
app.include_router(financial_statements.router, dependencies=_auth_dep)
app.include_router(standard_costing.router, dependencies=_auth_dep)
app.include_router(marginal_costing.router, dependencies=_auth_dep)
app.include_router(statement_forecast.router, dependencies=_auth_dep)
app.include_router(scenarios.router, dependencies=_auth_dep)
app.include_router(tax_codes.router, dependencies=_auth_dep)
app.include_router(fixed_assets.router, dependencies=_auth_dep)


@app.get("/health")
def health():
    return {"status": "ok"}
