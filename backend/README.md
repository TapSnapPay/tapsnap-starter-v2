# TapSnap Backend (FastAPI)

A minimal FastAPI backend with models for merchants, transactions, and payouts,
plus skeleton endpoints for onboarding, transactions, and Adyen webhooks.

## Quick start (Dev)

1. (Recommended) Create and activate a virtual env.
2. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy env and edit values:
   ```bash
   cp .env.example .env
   ```
4. Run the API:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open http://127.0.0.1:8000/docs

## Notes

- Uses SQLite by default for dev. Set `DATABASE_URL` to Postgres for prod.
- Webhook endpoint: `POST /api/v1/webhooks/adyen` (protect with basic auth + HMAC).
- Replace the stubs in `app/services/adyen.py` with real Adyen calls when ready.


---

## Postgres + Alembic (Migrations)

### Option A — Run Postgres via Docker (recommended)
From repo root:
```bash
docker compose up -d db
```
Set your `.env`:
```
DATABASE_URL=postgresql+psycopg2://tapsnap:tapsnap@localhost:5432/tapsnap
```
Then install deps and run migrations:
```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Option B — Run API + DB in Docker
```bash
docker compose up --build
```
The API will be on http://127.0.0.1:8000. Run Alembic migrations inside the `api` container if needed.

### Alembic commands
```bash
alembic revision --autogenerate -m "change message"
alembic upgrade head
alembic downgrade -1
```

## Simple Admin UI
Visit `http://127.0.0.1:8000/admin` to see merchants & transactions. This is a dev-only UI (no auth).
