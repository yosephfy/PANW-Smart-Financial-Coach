# Smart Financial Coach API

FastAPI service for ingestion, insights, subscription detection, and forecasting.

## Local Run
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/health` for a health check.

## CSV Ingestion
POST `/ingest/csv` with multipart form fields:
- `file`: CSV file
- `user_id`: string user id (e.g., `u_demo`)
- `default_account_id` (optional): used if CSV lacks `account_id`

Example (using sample CSV in repo):
```
curl -X POST \
  -F "file=@../../data/samples/transactions_sample.csv" \
  -F "user_id=u_demo" \
  -F "default_account_id=a_checking" \
  http://127.0.0.1:8000/ingest/csv
```

List transactions:
```
curl http://127.0.0.1:8000/users/u_demo/transactions?limit=20
```

### Deduplication
- Duplicates are detected during ingestion using a hash of `(user_id, date, amount_cents, merchant_lower)`.
- The service also queries the DB for existing rows with the same key and skips those.
- Helpful indexes are created in `db/schema.sql` to keep lookups fast.

### Categorization Provenance
- For each ingested row, the service stores `category_source` and `category_provenance` in `transactions`.
- Sources: `csv` (provided in file), `mcc` (from MCC mapping), `regex` (merchant/description match), `fallback` (none).
- Examples: `csv:groceries`, `mcc:5411`, `regex:streaming:spotify`, `none`.

## Categorization Explain
Dry-run categorization for a merchant/description/MCC. Useful for UI “Why this category?” tooltips or debugging mappings.

- GET `/categorization/explain?merchant=Starbucks&description=STARBUCKS%201234&mcc=5814`
- POST `/categorization/explain` with JSON body

Examples:
```
curl "http://127.0.0.1:8000/categorization/explain?merchant=Spotify&mcc=4899"

curl -X POST http://127.0.0.1:8000/categorization/explain \
  -H 'Content-Type: application/json' \
  -d '{"merchant":"Starbucks","description":"STARBUCKS 1234","mcc":"5814"}'
```

Response fields include:
- category: resolved category
- category_source: csv | mcc | regex | fallback
- category_provenance: e.g., csv:groceries | mcc:5411 | regex:streaming:spotify | none
- rule: matched rule id (e.g., streaming, coffee, mcc, csv, fallback)

## Subscriptions
Detect recurring subscriptions and list them.

POST `/subscriptions/detect`
```
curl -X POST http://127.0.0.1:8000/subscriptions/detect \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo"}'
```

GET `/users/{user_id}/subscriptions`
```
curl http://127.0.0.1:8000/users/u_demo/subscriptions
```

Heuristics:
- Groups negative transactions by merchant, checks median interval for weekly (~7d), monthly (~30d), yearly (~365d).
- Requires 3+ occurrences (monthly) or 4+ (weekly) with reasonable amount consistency.
- Computes `avg_amount` (median abs), `cadence`, `last_seen`, `status` (active/paused), and `price_change_pct` vs median.
