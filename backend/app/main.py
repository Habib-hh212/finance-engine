import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    budgets,
    cashflow,
    companies,
    controlling,
    financial_statements,
    insights,
    kpis,
    products,
    profitability,
    sales,
)
from app.auth import get_current_user
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
app.include_router(companies.router, dependencies=_auth_dep)
app.include_router(sales.router, dependencies=_auth_dep)
app.include_router(products.router, dependencies=_auth_dep)
app.include_router(budgets.router, dependencies=_auth_dep)
app.include_router(cashflow.router, dependencies=_auth_dep)
app.include_router(controlling.router, dependencies=_auth_dep)
app.include_router(profitability.router, dependencies=_auth_dep)
app.include_router(kpis.router, dependencies=_auth_dep)
app.include_router(insights.router, dependencies=_auth_dep)
app.include_router(financial_statements.router, dependencies=_auth_dep)


@app.get("/health")
def health():
    return {"status": "ok"}
