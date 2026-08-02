from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import budgets, cashflow, companies, controlling, insights, kpis, products, profitability, sales
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Finance Engine API", version="0.1.0", lifespan=lifespan)

# No auth yet (JWT is a later Phase 1 item), so CORS is the only gate right
# now — kept to local dev origins rather than "*". Add the deployed frontend
# origin here once the frontend actually gets deployed somewhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(sales.router)
app.include_router(products.router)
app.include_router(budgets.router)
app.include_router(cashflow.router)
app.include_router(controlling.router)
app.include_router(profitability.router)
app.include_router(kpis.router)
app.include_router(insights.router)


@app.get("/health")
def health():
    return {"status": "ok"}
