# Smart Financial Coach

**AI-powered personal finance coach** that turns your raw transaction history into clear, personalized insights.  
The app ingests CSV files or connects to Plaid, categorizes spending, detects recurring charges and gray-charges, forecasts your cash flow and savings goals, and surfaces friendly hints on how to save.

This hackathon project targets **students, young adults, freelancers and anyone who wants better money visibility**.

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

## ✨ Features

- **Transaction ingestion**: CSV upload or Plaid Sandbox integration.
- **Auto-categorization**: MCC, regex heuristics, AI fallback.
- **Subscription & gray-charge detector**: recurring & hidden fees.
- **Spending dashboard**: category breakdown, income vs expense.
- **Insights feed**: overspend alerts, trending merchants, save suggestions.
- **Forecasting**: cash flow projection + goal progress check.
- **Goals**: create, edit, monitor savings goals.
- **Anomalies**: Isolation Forest & heuristics for unusual charges.
- **Plaid integration**: sandbox accounts for safe demo.

---

## 🏗 Architecture

| Path                 | Purpose                                                  | Tech Stack                        |
| -------------------- | -------------------------------------------------------- | --------------------------------- |
| `apps/web`           | Frontend UI                                              | Next.js 14, Tailwind, shadcn/ui   |
| `services/api`       | Backend & ML services                                    | FastAPI, SQLAlchemy, scikit-learn |
| `db/schema.sql`      | Database schema                                          | Postgres                          |
| `services/api/app/*` | Domain logic (insights, subscriptions, anomalies, goals) | Python                            |

---

## 📊 Data Model

Tables defined in `db/schema.sql`:

- **users** – id, email, created_at
- **accounts** – id, user_id, type, name
- **transactions** – id, user_id, account_id, date, merchant, amount, category, flags
- **subscriptions** – merchant, avg_amount, period, next_expected
- **insights** – id, user_id, type, message, severity
- **goals** – target_amount, target_date, progress

Indexes: `(user_id, date)`, `(user_id, merchant)`

---

## 🤖 AI / Analytics

- **Categorization**: heuristic rules (MCC, regex), fallback ML classifier, confidence scores.
- **Subscription detection**: interval clustering (7/14/30/365 days), fuzzy merchant match.
- **Gray charges**: fees, small frequent charges, duplicates.
- **Anomalies**: Isolation Forest on merchant/category features + z-score check.
- **Forecasting**: rolling 3-month cashflow, simple projection, gap to goal.
- **Recurring classifier**: logistic regression model in `is_recurring_model.py`.

---

## ⚙️ Configuration

Environment variables (`.env.example`):

| Variable          | Required | Description             |
| ----------------- | -------- | ----------------------- |
| `DATABASE_URL`    | Yes      | Postgres connection URL |
| `PLAID_CLIENT_ID` | Optional | Plaid Sandbox ID        |
| `PLAID_SECRET`    | Optional | Plaid Sandbox secret    |
| `NEXT_PUBLIC_*`   | Maybe    | Frontend configs        |

---

## 🛠 Development

### Prereqs

- Node.js 18+, pnpm
- Python 3.10+
- Postgres

### Setup

```
# Backend
cd services/api
pip install -r requirements.txt

# Frontend
cd apps/web
pnpm install
```

### Run

```
# Backend API
uvicorn app.main:app --reload
# Frontend
pnpm dev
```

---

## ✅ Hackathon Deliverables

- Problem understanding → poor visibility & tedious manual tracking.
- Technical rigor → real algorithms (Isolation Forest, classifiers, heuristics).
- Creativity → explainable insights feed & save suggestions.
- Prototype quality → working ingestion, dashboard, insights, goals.
- AI application → categorization, anomaly detection, forecasting.
- Trust & security → sandbox only, transparent explanations.

---

## 🛣 Roadmap

- Real bank integrations post-hackathon.
- Mobile app (React Native).
- Enhanced ML categorizer & federated learning.
- Merchant negotiation assistant (cancel, discounts).
- Credit utilization & APR optimization.

---

## 📜 License

No LICENSE file present. For open use, MIT is recommended.
