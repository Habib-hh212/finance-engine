# Backend

FastAPI service covering the full Phase 1 backend scope: email/password auth (JWT), company setup + CSV sales import, Sales Forecasting, Budget Planning with a Manager → Finance → CFO approval chain, a rolling Cash Flow Forecast driven off both, Cost Controlling & Variance (budget vs. actual, budget consumption) with traffic-light status, Profitability Analysis (contribution margin by product/customer), a KPI Dashboard, a rule-based AI Insights engine, and Financial Statements (Income Statement + Balance Sheet) built from posted actuals. Phase 2 adds the Full Budget suite (Zero-Based, Flexible, Rolling, Capital), budget line edit/delete + version history on every submit, Standard Costing (8-variance method), and Marginal Costing / CVP analysis (break-even, margin of safety, operating leverage). Phase 3 adds Financial Statement Forecasting — projecting the Income Statement and Balance Sheet forward via driver linkages (AR/AP from Days Sales/Payable Outstanding, Cash from the existing Cash Flow Forecast, Equity rolled forward by net income).

No Alembic/migrations here yet — `backend/app/migrations.py` patches additive columns on app startup. Any new column added to an *already-existing* table needs an entry there in the same change, or it silently never reaches production (see ROADMAP.md §6e for the incident that taught us this).

## Auth

Every endpoint except `/auth/*` and `/health` requires `Authorization: Bearer <token>`. Get a token via `POST /auth/register` or `POST /auth/login`. There's no per-user company scoping yet — any logged-in user can see any company. That's a known Phase 1 gap, not an oversight; full multi-tenant RBAC is a later item.

Set `JWT_SECRET_KEY` via environment variable for anything beyond local dev — the fallback in `app/config.py` is intentionally insecure and only exists so the app runs without configuration out of the box.

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
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

`requirements-dev.txt` includes `requirements.txt` plus pytest/httpx/ruff; the Docker image installs only `requirements.txt`, so test tooling never ships in the runtime container.

## Tests

```
pytest
```

## Lint

```
ruff check .
```

## Sales CSV format

Required columns: `sku`, `period` (`YYYY-MM` or `YYYY-MM-DD`), `quantity`, `amount`, `currency`.
Optional: `product_name`, `customer_name`.

## Endpoints

- `POST /auth/register` — `{email, password, name}` → `{access_token}`
- `POST /auth/login` — `{email, password}` → `{access_token}`
- `GET /auth/me` — current user (requires the token)
- `POST /companies` — create a company
- `GET /companies` — list companies
- `POST /sales/upload?company_id=<uuid>` — upload a sales CSV (multipart `file`)
- `GET /sales/forecast?company_id=<uuid>&product_id=<uuid>&model=<model>&periods=<n>` — forecast the next `n` months
- `POST /gl-accounts?company_id=<uuid>` — create a GL account (`category`: `revenue` | `expense` | `asset` | `liability` | `equity`)
- `GET /gl-accounts?company_id=<uuid>` — list GL accounts
- `POST /budgets?company_id=<uuid>` — create a budget (`type`: `revenue` | `expense` | `master` | `zero_based` | `flexible` | `rolling` | `capital`), starts in `draft`. `rolling_window_months` defaults to 12 when `type` is `rolling` and it's omitted.
- `GET /budgets?company_id=<uuid>` / `GET /budgets/{id}` — list / fetch a budget (detail includes lines + approval history)
- `POST /budgets/{id}/lines` — add line items (only while `draft`); accepts `justification` (zero-based), `variable_rate_per_unit` (flexible), `useful_life_years` + `annual_cash_flow` (capital) as optional per-type fields
- `POST /budgets/{id}/submit` — moves `draft`/`rejected` → `pending_manager`; for `zero_based` budgets, rejects with 409 if any line is missing a `justification`
- `POST /budgets/{id}/approve` — advances the chain: `pending_manager` → `pending_finance` → `pending_cfo` → `approved` (locked)
- `POST /budgets/{id}/reject` — moves the current pending stage → `rejected`; resubmit to restart the chain
- `POST /budgets/{id}/roll-forward` — **rolling** budgets only, `draft` only: copies the latest period's lines one month forward and drops the oldest period, keeping `rolling_window_months` periods
- `GET /budgets/{id}/flexible-variance` — **flexible** budgets only: flexes each line's budget to `ActualLine.actual_quantity` and returns static/flexed/actual amounts plus spending variance (actual vs. flexed) and volume variance (flexed vs. static)
- `GET /budgets/{id}/capital-appraisal` — **capital** budgets only: payback period and simple ROI per line from `amount` (investment), `annual_cash_flow`, and `useful_life_years` — no NPV/IRR discounting
- `PATCH /budgets/{id}/lines/{line_id}` / `DELETE /budgets/{id}/lines/{line_id}` — edit or remove a line while status is `draft` or `rejected`
- `GET /budgets/{id}/versions` — every line snapshot taken at each `submit`, oldest first, so a reject → edit → resubmit cycle stays visible
- `POST /cashflow/items?company_id=<uuid>` — add a manual cash movement (`category`: `receivable_collection` | `payroll` | `vendor_payment` | `tax` | `loan` | `interest` | `other`; `direction`: `in` | `out`)
- `GET /cashflow/items?company_id=<uuid>` — list manual cash items
- `GET /cashflow/forecast?company_id=<uuid>&start_period=<YYYY-MM-DD>&periods=12&collection_lag_days=30&opening_balance=0` — rolling cash flow: cash-in from the sales forecast (shifted by the collection lag) + manual inflows, minus cash-out from **approved** expense budgets + manual outflows, with a running balance. Draft/pending budgets are excluded on purpose — they aren't a commitment yet. Assumes all contributing amounts are already in the company's base currency (FX conversion is a Phase 4 item).
- `POST /actuals?company_id=<uuid>` — post an actual amount against a GL account/period; optional `actual_quantity` feeds flexible-budget variance
- `GET /actuals?company_id=<uuid>&gl_account_id=<uuid>` — list actuals
- `GET /variance/budget-vs-actual?company_id=<uuid>&fiscal_year=<int>` — actual vs. **approved** budget by GL account/period, with variance amount, variance %, and traffic-light `status` (`green`/`yellow`/`red`) — direction-aware: expense overrun and revenue shortfall are unfavorable, the reverse is always green
- `GET /variance/budget-consumption/{budget_id}` — spent vs. remaining vs. total for a budget (any status — consumption is tracked through the approval cycle, not just after), with the same traffic-light `status`
- `GET /products?company_id=<uuid>` — list products (created automatically by sales CSV upload)
- `PATCH /products/{id}` — set `unit_variable_cost`, the input contribution-margin math needs
- `GET /profitability/by-product?company_id=<uuid>` — revenue, unit price, and contribution margin per product; null contribution fields when `unit_variable_cost` isn't set (never assumed zero)
- `GET /profitability/by-customer?company_id=<uuid>` — revenue and contribution margin per customer, aggregated across whatever products they bought
- `GET /kpis?company_id=<uuid>&fiscal_year=<int>&cash_start_period=<YYYY-MM-DD>&cash_opening_balance=0` — four KPIs pulled from the other modules: `gross_margin_pct` (from Profitability), `budget_utilization_pct` (from approved budgets), `forecast_accuracy_mape` (a real walk-forward backtest of the sales forecast model against history — not a stub), `cash_runway_months` (from Cash Flow Forecast; `null` if it omits `cash_start_period` or never goes negative in the 12-month window)
- `GET /ai/insights?company_id=<uuid>&fiscal_year=<int>` — rule-based (not ML) plain-language flags: budget overruns/shortfalls, unbudgeted spend, budget-consumption warnings, and forecasted sales declines, each with a `red`/`yellow` severity
- `GET /reports/income-statement?company_id=<uuid>&start_period=<YYYY-MM-DD>&end_period=<YYYY-MM-DD>` — revenue actuals minus expense actuals by GL account, for the period range
- `GET /reports/balance-sheet?company_id=<uuid>&as_of=<YYYY-MM-DD>` — cumulative balance of `asset`/`liability`/`equity` GL accounts as of a date (sum of every actual posted to that account up to and including that date). Reports `is_balanced` and `difference` rather than assuming assets always equal liabilities + equity — there's no double-entry enforcement, so it only balances if actuals were entered consistently.
- `POST /standard-costs?company_id=<uuid>` — upsert the standard cost sheet for a product (material price/qty, labor rate/hours, variable + fixed overhead rates, budgeted fixed overhead); a second POST for the same product updates it in place
- `GET /standard-costs?company_id=<uuid>` — list standard cost sheets
- `POST /production-actuals?company_id=<uuid>` — post what actually happened in production for a product/period (units produced, actual material/labor/overhead figures)
- `GET /production-actuals?company_id=<uuid>` — list production actuals
- `GET /standard-costing/variance?company_id=<uuid>&fiscal_year=<int>` — the 8-variance method (material price/quantity, labor rate/efficiency, variable overhead spending/efficiency, fixed overhead budget/volume) for every product with both a standard and an actual on file; positive is favorable, negative unfavorable
- `POST /fixed-costs?company_id=<uuid>` — record a fixed (period, not per-unit) cost for a fiscal year
- `GET /fixed-costs?company_id=<uuid>&fiscal_year=<int>` — list fixed costs
- `GET /marginal-costing/summary?company_id=<uuid>&fiscal_year=<int>` — CVP analysis: revenue, variable cost, contribution margin (+ ratio), fixed costs, net operating income, break-even revenue, margin of safety (+ %), degree of operating leverage — company-level off the weighted-average contribution margin ratio; products missing `unit_variable_cost` are excluded and listed in `uncosted_product_skus`
- `PATCH /gl-accounts/{id}` — set `forecast_role` (`cash` | `accounts_receivable` | `accounts_payable` | `null`) on a GL account, so it feeds the right Balance Sheet Forecast line
- `GET /forecast/income-statement?company_id=<uuid>&start_period=<YYYY-MM-DD>&periods=12` — projects revenue (from the existing sales forecast) and expense (from approved budget lines on `expense`-category GL accounts) forward by calendar month
- `GET /forecast/balance-sheet?company_id=<uuid>&start_period=<YYYY-MM-DD>&periods=12&dso_days=45&dpo_days=30&collection_lag_days=30` — projects AR/AP via Days Sales/Payable Outstanding against the income statement forecast, Cash by reusing the Cash Flow Forecast, Equity by rolling actual equity forward with forecasted net income (no dividends/capital transactions modeled), and every other account flat. `is_balanced`/`difference` here double as the projection's implied financing gap or surplus, not just a balance check
