# Backend

FastAPI service covering the full Phase 1 backend scope: company setup + CSV sales import, Sales Forecasting, Budget Planning with a Manager → Finance → CFO approval chain, a rolling Cash Flow Forecast driven off both, Cost Controlling & Variance (budget vs. actual, budget consumption) with traffic-light status, Profitability Analysis (contribution margin by product/customer), a KPI Dashboard, and a rule-based AI Insights engine.

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
- `GET /products?company_id=<uuid>` — list products (created automatically by sales CSV upload)
- `PATCH /products/{id}` — set `unit_variable_cost`, the input contribution-margin math needs
- `GET /profitability/by-product?company_id=<uuid>` — revenue, unit price, and contribution margin per product; null contribution fields when `unit_variable_cost` isn't set (never assumed zero)
- `GET /profitability/by-customer?company_id=<uuid>` — revenue and contribution margin per customer, aggregated across whatever products they bought
- `GET /kpis?company_id=<uuid>&fiscal_year=<int>&cash_start_period=<YYYY-MM-DD>&cash_opening_balance=0` — four KPIs pulled from the other modules: `gross_margin_pct` (from Profitability), `budget_utilization_pct` (from approved budgets), `forecast_accuracy_mape` (a real walk-forward backtest of the sales forecast model against history — not a stub), `cash_runway_months` (from Cash Flow Forecast; `null` if it omits `cash_start_period` or never goes negative in the 12-month window)
- `GET /ai/insights?company_id=<uuid>&fiscal_year=<int>` — rule-based (not ML) plain-language flags: budget overruns/shortfalls, unbudgeted spend, budget-consumption warnings, and forecasted sales declines, each with a `red`/`yellow` severity
