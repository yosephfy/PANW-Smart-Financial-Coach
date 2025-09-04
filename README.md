# PANW Smart Financial Coach

An AI-powered personal finance coach that turns raw transactions into personalized insights, detects subscriptions/gray charges, and helps users hit savings goals.

## MVP Scope (Hackathon)
- Transaction ingest (CSV now; Plaid Sandbox later)
- Categorization heuristics (merchant/description mapping)
- Insights feed (overspend, anomaly, trending up, subscription alerts)
- Subscription detector (recurrence + price change)
- Simple goal forecasting (cash flow vs target)

## Stack
- Frontend: Next.js + TypeScript + Tailwind (to be added)
- Backend: FastAPI (Python)
- DB: PostgreSQL (dev: SQLite acceptable), SQL schema in `db/schema.sql`

## Getting Started (Backend)
1) Create a virtualenv and install deps:
   - `cd services/api`
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`

2) Run the API locally:
   - `uvicorn app.main:app --reload`
   - Open `http://localhost:8000/health` for a health check.

## Getting Started (Frontend)
1) Open a new terminal:
   - `cd apps/web`
   - `npm install`
   - `export NEXT_PUBLIC_API_URL=http://localhost:8000` (optional; defaults to this)
   - `npm run dev`
   - Open `http://localhost:3000`

Pages:
- `/ingest` upload CSV and ingest
- `/transactions` list user transactions
- `/subscriptions` detect + list subscriptions
- `/plaid` connect Plaid Sandbox, then import transactions

## Plaid Sandbox Setup
Set environment variables before running the API:
```
export PLAID_CLIENT_ID=your_sandbox_client_id
export PLAID_SECRET=your_sandbox_secret
export PLAID_HOST=https://sandbox.plaid.com
```
Then open the frontend `/plaid` page to connect a sandbox bank and import transactions.

## Repo Structure
```
PANW-Smart-Financial-Coach/
├─ apps/
│  └─ web/                 # Next.js app (placeholder)
├─ services/
│  └─ api/                 # FastAPI service
│     ├─ app/
│     │  └─ main.py        # API entrypoint
│     └─ requirements.txt
├─ db/
│  └─ schema.sql           # Initial tables for users/transactions/etc.
└─ data/
   └─ samples/
      └─ transactions_sample.csv
```

## Next Steps
- Add CSV ingestion endpoint and normalization
- Implement categorization heuristics and subscription detection
- Scaffold Next.js dashboard and insights feed

Contributing: see `CONTRIBUTING.md` for the alignment checklist and PR template to ensure every change maps to the hackathon brief in `CASE_STUDY.md`.
See the full hackathon brief in `CASE_STUDY.md`. We reference this spec when adding features to ensure alignment with goals (AI-powered insights, personalization, security/trust, and demo readiness).
