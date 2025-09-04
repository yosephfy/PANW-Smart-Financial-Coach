# Smart Financial Coach

**AI-powered personal finance coach** that turns your raw transaction history into clear, personalized insights.  
The app ingests CSV files or connects to Plaid, categorizes spending, detects recurring charges and gray-charges, forecasts your cash flow and savings goals, and surfaces friendly hints on how to save.

This hackathon project targets **students, young adults, freelancers and anyone who wants better money visibility**.

## VIDEO PRESENTATION LINK:

<<<<<<< HEAD
<<<<<<< HEAD
(https://vimeo.com/1115991923?share=copy)

## Interactive DEMO:

# [https://77f083019ea3.ngrok-free.app](https://77f083019ea3.ngrok-free.app)

# [https://vimeo.com/1115981585?share=copy](https://vimeo.com/1115981585?share=copy)

[https://vimeo.com/1115981585?share=copy](https://vimeo.com/1115981585?share=copy)](https://vimeo.com/1115991923?share=copy)

> > > > > > > c9d39d8 (Fix video presentation link in README)

## Interactive DEMO:

[https://e31edb5d3763.ngrok-free.app](https://e31edb5d3763.ngrok-free.app)

> > > > > > > 061b22b (Add video presentation and demo links to README)

---

## 🚀 Quick Start (Demo)

```
# Backend
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd apps/web
pnpm install
pnpm dev
```

Then open [http://localhost:3000](http://localhost:3000).

---

## ✨ Features (What’s Implemented)

- **Transaction ingestion**: CSV upload or Plaid Sandbox integration.
- **Auto-categorization**: MCC, regex heuristics, AI fallback (per-user models).
- **Subscription & gray-charge detector**: recurring & hidden fees detection and management UI.
- **Spending dashboard**: category breakdown, income vs expense, daily trends.
- **Insights feed**: overspend alerts, trending merchants, suggested savings.
- **Forecasting**: cash flow projection + goal progress and suggestions.
- **Goals**: create, edit, monitor savings goals and auto-funding suggestions.
- **Anomalies**: Isolation Forest & heuristics for unusual charges.
- **Admin / Developer menu**: endpoints and UI for running detection, importing sandbox Plaid data, and triggering insights.

## ✅ Hackathon Deliverables Mapping

- **Problem understanding:** addresses visibility and behavior change for spenders
- **Technical rigor:** ML pipelines (categorization, recurring detection, anomaly), background tasks, caching
- **Creativity:** Explainable insight feed, per-user models, developer tools for testing endpoints
- **Prototype quality:** CSV ingestion, Plaid sandbox integration, dashboards and subscription management
- **AI application:** TF-IDF + LogisticRegression, IsolationForest, LLM-powered rewrites
- **Trust & security:** sandbox usage, JWT/session patterns, caching to limit LLM calls

---

| Path                 | Purpose                                          | Tech Stack                         |
| -------------------- | ------------------------------------------------ | ---------------------------------- |
| `apps/web`           | Frontend UI                                      | Next.js (TypeScript), Tailwind CSS |
| `services/api`       | Backend & ML services                            | FastAPI, scikit-learn, joblib      |
| `services/api/app/*` | Domain logic (ingest, insights, subs, forecasts) | Python                             |
| `db/schema.sql`      | DB schema / migrations                           | SQLite (dev) / Postgres (prod)     |
| `demo_data/`         | Persona CSVs & seeds                             | CSV files for Ava & Milo personas  |

---

## 🌐 CORE WEB FRAMEWORK

**Framework:** FastAPI (v0.111.0)
**Description:** Modern, high-performance web framework for building APIs.

**Key features & implementation highlights**

- Automatic API documentation (Swagger/OpenAPI)
- Pydantic for type validation
- Async/await endpoints for performance
- CORS middleware and JWT-based security support
- 40+ API endpoints across 9 categories (AI & ML, Forecasting, Insights, Goals, Subscriptions, Cash Flow, Transactions, Budget, Ingestion)
- Real-time transaction processing, background tasks, DB pooling, and robust error handling

**Endpoint Categories**

- AI & ML Services (categorization, anomaly detection)
- Forecasting & Predictions
- Financial Insights Generation
- Goal Management & Auto-funding
- Subscription Detection & Management
- Cash Flow Analysis
- Transaction Processing
- Budget Management
- Data Ingestion (CSV, Plaid API)

---

## 🤖 MACHINE LEARNING STACK

**Primary library:** scikit-learn (v1.5.1)

**Algorithms & pipelines**

- **TF-IDF Vectorization**

  - Purpose: convert transaction descriptions to features
  - Implementation: `TfidfVectorizer` with ngram_range=(1,2), max_features=30000

- **Logistic Regression**

  - Purpose: classification for transaction categorization and recurring detection
  - Implementation: `LogisticRegression` (class_weight='balanced', max_iter \~ 200–300)

- **Isolation Forest**

  - Purpose: anomaly detection for unusual spending
  - Implementation: `IsolationForest` with contamination \~ 0.08

- **Ridge Regression**

  - Purpose: forecasting and trend analysis for cashflow/amount predictions

**ML Pipelines**

- **Transaction Categorizer Pipeline**

  - TF-IDF → Logistic Regression → cross-validation → per-user model persistence

- **Recurring Transaction Pipeline**

  - Feature engineering (merchant tokens, amount/time features) → TF-IDF → LogisticRegression

- **Anomaly Detection Pipeline**

  - Historical feature extraction → IsolationForest → real-time scoring

---

## 💾 MODEL PERSISTENCE SYSTEM

**Library:** joblib (v1.4.2)

- Fast serialization/deserialization for scikit-learn models, compressed binary format.
- **Model storage layout (examples)**:

  - `ai_categorizer/global.joblib` (universal)
  - `ai_categorizer/user1.joblib`, `user2.joblib` (per-user)
  - `is_recurring/user1.joblib` (recurring detectors)

- **Fallback**: JSON token-frequency fallback models if scikit-learn isn't available (ensures basic categorization without heavy dependencies).

---

## 🧠 AI INTEGRATION STACK

**OpenAI Integration**

- Library: `openai` (client)
- Uses: insight rewriting, and on-demand friendly tone rewriting for UI copy.
- Implementation: asynchronous background threading system that queues LLM rewrite requests, caches results, and updates insight records when rewrites are ready.

**LLM capabilities**

- Insight personalization and rewrite
- Natural-language transaction categorization (optional)
- Contextual spending pattern analysis

---

## 🗄️ DATABASE TECHNOLOGY

**Default (dev):** SQLite (via built-in `sqlite3`)
**Production:** Postgres (supported; update `DATABASE_URL`)

**Key schema features**

- ACID compliance, foreign keys, row-factory dict access
- Transaction provenance tracking
- Goals with milestones and contribution tracking
- Subscription tracking and recurring detection metadata
- Insights caching and LLM enhancement fields
- Deduplication logic and CSV import/export capabilities

**Data management**

- Automated migration scripts
- Batch processing for large imports
- Connection pooling and safe concurrent access patterns

---

## 🔌 EXTERNAL INTEGRATIONS & CLIENTS

- **Plaid API** (library: `plaid-python`, v18.0.0) — sandbox bank connection and transaction sync
- **HTTP client:** `httpx` for async HTTP requests, pooling, timeout management
- **Security helpers:** `itsdangerous`, `hmac`, `hashlib`, `pyjwt` (JWT handling)

---

## 🖥️ FRONTEND TECHNOLOGY

- **Framework:** Next.js (TypeScript)
- **Styling:** Tailwind CSS
- **UI features:** responsive dashboard, charts (Recharts), interactive filters, developer/debug views
- **Developer tools:** built-in dev API calls, 40+ endpoint testing utilities in the dev environment, developer mode for debugging

---

## ⚡ ADVANCED FEATURES

- **Real-time processing**: live categorization, instant anomaly detection, subscription identification, dynamic insights
- **Intelligent automation**: auto-funding suggestions, smart budget adjustments, auto-scheduling transfers (simulated)
- **Scalability**: per-user model training/persistence, efficient model caching, background tasks for heavy workloads
- **Data science**: time-series analysis, feature engineering, cross-validation and evaluation for models

---

## 🚀 DEPLOYMENT STACK

- **Server:** Uvicorn ASGI (production server for FastAPI)
- **Features:** hot reloading (dev), WebSocket support, graceful shutdowns
- **Dev tools:** Makefile, CSV loaders, model training automation scripts
- **Production considerations:** env variable configuration, DB path flexibility, robust error logging, security middleware

---

## 📊 METRICS & EXECUTIVE SUMMARY

**Executive Summary**

- Architecture: FastAPI backend + Next.js frontend (modern microservices-style)
- AI/ML: 3 distinct ML pipelines (Categorization, Recurring Detection, Anomaly Detection)
- Category model: TF-IDF + Logistic Regression for transaction categorization
- Anomaly detection: IsolationForest for unusual spending detection
- Recurring detection: ML-backed subscription identification
- Persistence: Joblib with JSON fallback
- LLM Integration: OpenAI for insight rewriting and personalization
- Data layer: SQLite for dev, Postgres supported for prod
- Integrations: Plaid API, HTTPX for async calls
- Developer tools: 40+ endpoints, built-in API docs (OpenAPI)

**Key Metrics**

- 40+ API endpoints across 9 categories
- 3 production ML pipelines implemented
- 12+ core Python libraries/frameworks in use
- Real-time processing (targets <100ms for light requests)
- Per-user model persistence and caching for scalability

---

## ⚙️ Configuration (ENV)

| Variable              | Required | Description                            |
| --------------------- | -------- | -------------------------------------- |
| `DATABASE_URL`        | Yes      | DB connection string (sqlite/postgres) |
| `PLAID_CLIENT_ID`     | Optional | Plaid sandbox client id                |
| `PLAID_SECRET`        | Optional | Plaid sandbox secret                   |
| `OPENAI_API_KEY`      | Optional | OpenAI key for insight rewrites        |
| `NEXT_PUBLIC_API_URL` | Maybe    | Frontend -> backend API base URL       |

> Note: For local demos, default `user1` is used by many frontend pages — see `apps/web` code.

---

## 🛠 Development & Run

### Prereqs

- Node 18+, pnpm
- Python 3.10+
- (Optional) Postgres for production

### Setup

```
# Backend
cd services/api
pip install -r requirements.txt

# Frontend
cd apps/web
pnpm install
```

### Run (dev)

```
# Backend
uvicorn app.main:app --reload --port 8000

# Frontend
pnpm dev
```
