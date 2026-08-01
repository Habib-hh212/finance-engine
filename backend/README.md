# Backend

FastAPI service: company setup, CSV-based sales import, Sales Forecasting (moving average / weighted average / exponential smoothing), and Budget Planning with a Manager → Finance → CFO approval chain.

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
- `POST /gl-accounts?company_id=<uuid>` — create a GL account (`category`: `revenue` | `expense`)
- `GET /gl-accounts?company_id=<uuid>` — list GL accounts
- `POST /budgets?company_id=<uuid>` — create a budget (`type`: `revenue` | `expense` | `master`), starts in `draft`
- `GET /budgets?company_id=<uuid>` / `GET /budgets/{id}` — list / fetch a budget (detail includes lines + approval history)
- `POST /budgets/{id}/lines` — add line items (only while `draft`)
- `POST /budgets/{id}/submit` — moves `draft`/`rejected` → `pending_manager`
- `POST /budgets/{id}/approve` — advances the chain: `pending_manager` → `pending_finance` → `pending_cfo` → `approved` (locked)
- `POST /budgets/{id}/reject` — moves the current pending stage → `rejected`; resubmit to restart the chain
