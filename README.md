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
   - Open `http://127.0.0.1:8000/health` for a health check.

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
