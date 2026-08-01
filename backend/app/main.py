from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import budgets, cashflow, companies, controlling, sales
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Finance Engine API", version="0.1.0", lifespan=lifespan)

app.include_router(companies.router)
app.include_router(sales.router)
app.include_router(budgets.router)
app.include_router(cashflow.router)
app.include_router(controlling.router)


@app.get("/health")
def health():
    return {"status": "ok"}
