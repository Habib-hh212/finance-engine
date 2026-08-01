from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import budgets, cashflow, companies, controlling, insights, kpis, products, profitability, sales
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Finance Engine API", version="0.1.0", lifespan=lifespan)

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
