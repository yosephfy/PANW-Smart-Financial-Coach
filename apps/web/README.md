# Web App (Next.js)

Minimal Next.js frontend to interact with the FastAPI backend.

## Quick Start
- cd `apps/web`
- set API URL (optional): `export NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
- install deps: `npm install`
- run dev: `npm run dev`
- open: http://localhost:3000

Pages:
- `/ingest` — upload CSV to import transactions
- `/transactions` — view latest transactions (with categorization provenance)
- `/subscriptions` — detect and list recurring subscriptions
