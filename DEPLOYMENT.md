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

There's no migration tool wired up yet (no Alembic). After changing a SQLAlchemy model, apply it to Neon directly:

```bash
cd backend
DATABASE_URL="<neon connection string>" python3 -c "
from app.database import Base, engine
import app.models
Base.metadata.create_all(bind=engine)
"
```

`create_all` only adds missing tables/columns it doesn't know about — it won't alter or drop existing ones. That's fine for adding new tables, not for changing existing column types; a real migration tool is needed before this schema stabilizes further.

## Known gaps

- No per-user company scoping — any authenticated user can see every company in the database. Fine for a single team's internal use, not for multiple unrelated customers.
- No custom domain — using the `*.vercel.app` URLs Vercel assigns by default.
