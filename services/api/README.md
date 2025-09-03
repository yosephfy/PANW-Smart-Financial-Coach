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

## Insights
Generate and list insights (overspend, trending, merchant anomaly, save suggestions):

POST `/insights/generate`
```
curl -X POST http://127.0.0.1:8000/insights/generate \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo"}'
```

GET `/users/{user_id}/insights`
```
curl http://127.0.0.1:8000/users/u_demo/insights
```

Notes:
- Category overspend/trending compare current 30d vs previous 30d only if the previous window has sufficient signal (>=3 expense tx and >=$50 spend in that category). This avoids false increases when there’s no prior data.
- Merchant anomaly: last charge vs 90d mean/std; flags >2.5σ.
- Save suggestions: top discretionary categories with ~20% cut potential.

## Plaid Sandbox
Enable Plaid with Sandbox credentials as environment variables when running the API:

## Anomaly Detection (IsolationForest)
Detect personalized outliers using IsolationForest per merchant (6-month window). Detected items are upserted into `insights` as `ml_outlier`.

```
curl -X POST http://127.0.0.1:8000/anomaly/iforest/detect \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","contamination":0.08}'
```

## Forecast (Categories)
Simple next-month forecast per category using weighted recent months.

```
curl -X POST http://127.0.0.1:8000/forecast/categories \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","months_history":6,"top_k":8}'
```

## LLM Insight Rewriter (Optional)
Rewrite an insight’s title/body to a friendlier tone using OpenAI. Requires `OPENAI_API_KEY` set and `openai` installed.

```
export OPENAI_API_KEY=sk-...
curl -X POST http://127.0.0.1:8000/insights/rewrite \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","insight_id":"<id-from-insights>","tone":"friendly"}'
```

## AI Categorizer (ML)
Optional TF‑IDF + Logistic Regression model to categorize merchants/descriptions. The API runs without it; install deps and train to enable.

Install deps (already in requirements.txt) and train on your user’s existing transactions:
```
pip install -r requirements.txt
curl -X POST http://127.0.0.1:8000/ai/categorizer/train \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","min_per_class":5}'
```

Predict for a text snippet:
```
curl -X POST http://127.0.0.1:8000/ai/categorizer/predict \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","merchant":"Starbucks","description":"STARBUCKS 1234","top_k":3}'
```

Auto-use during ingestion:
- If a trained model exists for the `user_id`, ingestion will apply the model when the heuristic category is missing/low-signal (fallback/regex). If model confidence ≥ 0.7, it sets `category_source=ml` and `category_provenance=ml:<label>:<prob>`.
```
export PLAID_CLIENT_ID=your_sandbox_client_id
export PLAID_SECRET=your_sandbox_secret
export PLAID_HOST=https://sandbox.plaid.com
uvicorn app.main:app --reload
```

Endpoints:
- POST `/plaid/link/token/create` { user_id }
- POST `/plaid/link/public_token/exchange` { user_id, public_token }
- POST `/plaid/transactions/import` { user_id, start_date?, end_date? }

Flow:
1) Frontend calls link/token/create to obtain `link_token` and launches Plaid Link.
2) On success, frontend sends `public_token` to `public_token/exchange` which stores access token + item for the user.
3) Call `/plaid/transactions/import` to fetch transactions and persist them (category mapped with provenance; expenses negative; income positive).
