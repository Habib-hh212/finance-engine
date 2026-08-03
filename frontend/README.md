# Frontend

React + TypeScript + Material UI, covering all Phase 1 backend modules: Dashboard (KPIs + AI Insights), Sales Forecasting, Budget Planning, Cash Flow Forecast, Cost Controlling & Variance, Profitability, and Financial Statements (Income Statement + Balance Sheet). Budget Planning also covers the Phase 2 Full Budget suite (Zero-Based, Flexible, Rolling, Capital) plus inline line editing/deleting and an expandable version-history trail on every submit. Profitability includes a Marginal Costing (CVP) section — fixed costs, break-even revenue, margin of safety, operating leverage. A dedicated Standard Costing page covers the standard cost sheet, production actuals, and the 8-variance method. Financial Statements includes a Phase 3 forecast section projecting the Income Statement and Balance Sheet forward (DSO/DPO/collection-lag inputs); Budget Planning's GL Account list lets you tag an account's forecast role (cash/AR/AP) to feed it. Sales Forecasting's model dropdown includes two ML options (Random Forest, Gradient Boosting) alongside the statistical models, plus a "Compare models" panel showing walk-forward MAPE accuracy for every model side by side, and a "Demand prediction" panel forecasting units instead of revenue. Profitability adds a Customer Churn Risk table (recency/frequency ratio, not a trained classifier). A new Scenario Planning page lets you create named what-if growth assumptions and compares the resulting Income Statement/Balance Sheet forecast against the base case side by side. The Dashboard's AI Insights list now also includes statistical spend/sales anomalies (a z-score against each account's/product's own history), not just the fixed-threshold budget rules.

## Run

```
cp .env.example .env.local   # point VITE_API_BASE_URL at your backend
npm install
npm run dev
```

Requires the backend running (see `../backend/README.md`) — the API's CORS config allows `http://localhost:5173` by default.

## Stack

- **Routing**: react-router-dom, lazy-loaded per page (AG Grid and ECharts are heavy — only the pages that use them pull them in)
- **UI**: MUI
- **Charts**: ECharts via `echarts-for-react`, wrapped in `src/components/EChart.tsx` — that wrapper forces a `resize()` on mount via `requestAnimationFrame`. Without it, charts can initialize against a container that hasn't finished its layout pass yet and silently render axes/legend with no series geometry (bars especially). Always use `<EChart>` for new charts, not `<ReactECharts>` directly.
- **Tables**: AG Grid Community, used where rows are edited (budget line items)
- **State**: no global store — `CompanyContext` holds the selected company (persisted to `localStorage`), each page fetches its own data

## Structure

- `src/api/` — typed fetch wrappers + TypeScript types mirroring the backend's Pydantic schemas, one file per backend module
- `src/context/CompanyContext.tsx` — company list/selection, gates the whole app until one exists (`CompanyGate`)
- `src/components/` — shared UI: `Layout` (nav shell), `CompanyGate`, `StatusPill` (traffic-light chip), `EChart`
- `src/pages/` — one file per module, matching the sidebar

## Known gaps

- No auth (matches backend — JWT is a later Phase 1 item)
- No automated tests yet (backend has 38; frontend has none — component/integration tests would be the next addition)
- Bundle is still large per-chunk (AG Grid ~1MB, ECharts ~1.1MB) even after route-level code splitting; further splitting would need per-feature dynamic imports within those pages
