# Deployment

Live at:
- Frontend: https://finance-engine-frontend.vercel.app
- Backend: https://finance-engine-backend.vercel.app

## Stack

- **Frontend**: Vercel (static Vite build), project `finance-engine-frontend`, rooted at `frontend/`.
- **Backend**: Vercel Python serverless functions, project `finance-engine-backend`, rooted at `backend/`. The entrypoint is `backend/api/index.py`, which just re-exports the FastAPI `app` from `app.main` — Vercel's Python runtime auto-detects a top-level `app`/`handler` under `api/` and wraps it as ASGI. No `vercel.json` is needed; an earlier attempt at a catch-all rewrite actually broke routing (Vercel now routes using the *rewritten* destination path for backend-framework projects, not the original request path — removing the rewrite and relying on Vercel's native FastAPI detection fixed it).
- **Database**: Neon (Postgres), free tier, project `finance-engine`. Uses the pooler connection string (`...-pooler.<region>.aws.neon.tech`), which handles the connect/reconnect churn of serverless functions much better than the direct host.

## Why this combo

Railway's free tier is a 30-day trial, not indefinite. Render's free tier now requires a card on file for identity verification (no charge unless you exceed limits, but still a card). Vercel's Hobby plan needed no card for either project, so the backend went there too, using their Python serverless support instead of a normal Docker/always-on server.

**Trade-off**: cold starts after idle periods, and each request has to complete within Vercel's free-tier execution limit (~10s). Fine for this app's current usage (no long-running jobs), but worth revisiting — e.g. moving back to a paid always-on host — if traffic or per-request work grows.

## Environment variables

Backend (`vercel env` on the `finance-engine-backend` project):
- `DATABASE_URL` — Neon pooler connection string, `postgresql+psycopg2://...`
- `JWT_SECRET_KEY` — random secret (generated with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`); rotate this to invalidate all existing sessions
- `FRONTEND_ORIGINS` — comma-separated allowed CORS origins; currently just the frontend's Vercel URL

Frontend (`vercel env` on the `finance-engine-frontend` project):
- `VITE_API_BASE_URL` — the backend's Vercel URL

## Redeploying

```bash
# Backend
cd backend && vercel --prod

# Frontend
cd frontend && vercel --prod
```

Both projects are linked (`.vercel/` directories, gitignored) so `vercel --prod` picks up the right project automatically. If a fresh checkout needs relinking: `vercel link --project finance-engine-backend` (or `-frontend`).

## Database schema changes

There's no migration tool wired up yet (no Alembic). `app.main`'s lifespan runs two steps on every startup: `Base.metadata.create_all(bind=engine)`, which creates any *table* the live database doesn't have yet, then `app.migrations.apply_additive_columns(engine)`, which inspects each existing table and adds any *column* listed in `ADDITIVE_COLUMNS` that's missing.

**`create_all` on its own does not add columns to a table that already exists** — this bit us for real: several columns added to `budgets`/`budget_lines`/`actual_lines` during Phase 2 shipped, passed local tests (a fresh SQLite DB always has the full current schema), and simply never reached the live Neon Postgres table. Every budget creation and every actuals post 500'd in production until it was caught by accident days later, not by any deploy check.

**So: any new column on an already-existing table needs a matching entry added to `ADDITIVE_COLUMNS` in `backend/app/migrations.py`, in the same change that adds the model field.** New tables don't need an entry — `create_all` handles those correctly on its own. After deploying, verify with a real write against the live API (a `curl POST`, not just checking the route exists in `/docs` or `openapi.json`) — that's the only check that actually would have caught the incident above.

A real migration tool (Alembic) is still worth adding before this schema stabilizes further; the startup patch only handles additive nullable columns, not renames, drops, or type changes.

## Serverless package size

Vercel Python serverless functions have a size ceiling (250MB unzipped on Hobby). This is the reason ML Forecasting uses scikit-learn (`sklearn` + `scipy`, ~130MB combined) rather than XGBoost, Prophet, or an LSTM/TensorFlow stack — those each add either a large native binary or a full deep-learning/probabilistic-programming dependency tree that risks blowing the limit and badly hurting cold-start time. If a future model genuinely needs one of those, moving the backend off Vercel serverless (back to an always-on host) would need to happen first.

## Known gaps

- No per-user company scoping — any authenticated user can see every company in the database. Fine for a single team's internal use, not for multiple unrelated customers.
- No custom domain — using the `*.vercel.app` URLs Vercel assigns by default.
