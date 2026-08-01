# Backend

FastAPI service: company setup, CSV-based sales import, and Sales Forecasting (moving average / weighted average / exponential smoothing).

## Run with Docker (recommended)

From the repo root:

```
docker compose up --build
```

API available at `http://localhost:8000`, docs at `http://localhost:8000/docs`.

## Run locally

Requires Python 3.12 and a running PostgreSQL instance matching `DATABASE_URL` (see `.env.example`).

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tests

```
pytest
```

## Sales CSV format

Required columns: `sku`, `period` (`YYYY-MM` or `YYYY-MM-DD`), `quantity`, `amount`, `currency`.
Optional: `product_name`, `customer_name`.

## Endpoints

- `POST /companies` — create a company
- `GET /companies` — list companies
- `POST /sales/upload?company_id=<uuid>` — upload a sales CSV (multipart `file`)
- `GET /sales/forecast?company_id=<uuid>&product_id=<uuid>&model=<model>&periods=<n>` — forecast the next `n` months
