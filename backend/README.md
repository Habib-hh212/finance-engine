# Backend

FastAPI service covering all four Phase 1 modules: company setup + CSV sales import, Sales Forecasting, Budget Planning with a Manager → Finance → CFO approval chain, a rolling Cash Flow Forecast driven off both, and Cost Controlling & Variance (budget vs. actual, budget consumption) with traffic-light status.

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
- `POST /cashflow/items?company_id=<uuid>` — add a manual cash movement (`category`: `receivable_collection` | `payroll` | `vendor_payment` | `tax` | `loan` | `interest` | `other`; `direction`: `in` | `out`)
- `GET /cashflow/items?company_id=<uuid>` — list manual cash items
- `GET /cashflow/forecast?company_id=<uuid>&start_period=<YYYY-MM-DD>&periods=12&collection_lag_days=30&opening_balance=0` — rolling cash flow: cash-in from the sales forecast (shifted by the collection lag) + manual inflows, minus cash-out from **approved** expense budgets + manual outflows, with a running balance. Draft/pending budgets are excluded on purpose — they aren't a commitment yet. Assumes all contributing amounts are already in the company's base currency (FX conversion is a Phase 4 item).
- `POST /actuals?company_id=<uuid>` — post an actual amount against a GL account/period
- `GET /actuals?company_id=<uuid>&gl_account_id=<uuid>` — list actuals
- `GET /variance/budget-vs-actual?company_id=<uuid>&fiscal_year=<int>` — actual vs. **approved** budget by GL account/period, with variance amount, variance %, and traffic-light `status` (`green`/`yellow`/`red`) — direction-aware: expense overrun and revenue shortfall are unfavorable, the reverse is always green
- `GET /variance/budget-consumption/{budget_id}` — spent vs. remaining vs. total for a budget (any status — consumption is tracked through the approval cycle, not just after), with the same traffic-light `status`
