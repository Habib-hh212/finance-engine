from fastapi import FastAPI

from app.api import companies, sales
from app.database import Base, engine

app = FastAPI(title="Finance Engine API", version="0.1.0")

app.include_router(companies.router)
app.include_router(sales.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
