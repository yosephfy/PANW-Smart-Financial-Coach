from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from . import db as db_mod
from .ingest import parse_csv_transactions, dupe_hash, categorize_with_provenance
from pydantic import BaseModel
from .insights import generate_insights, upsert_insights
from .subscriptions import detect_subscriptions_for_user, upsert_subscriptions
from .anomaly import detect_iforest_insights
from .forecast import forecast_categories
try:
    from .llm import rewrite_insight_llm
    LLM_AVAILABLE = True
except Exception:
    LLM_AVAILABLE = False

# Make Plaid optional so the API can start without plaid-python installed
try:
    from .plaid_integration import (
        create_link_token as _create_link_token,
        exchange_public_token as _exchange_public_token,
        import_transactions_for_user as _import_transactions_for_user,
    )
    PLAID_AVAILABLE = True
except Exception:
    PLAID_AVAILABLE = False
    def _unavailable(*_args, **_kwargs):
        raise HTTPException(
            status_code=503,
            detail="Plaid integration unavailable. Install plaid-python and set PLAID_CLIENT_ID/PLAID_SECRET.",
        )
    _create_link_token = _unavailable
    _exchange_public_token = _unavailable
    _import_transactions_for_user = _unavailable

# Optional ML categorizer (AI)
try:
    from .ai_categorizer import (
        train_for_user as _train_categorizer,
        predict_for_user as _predict_categorizer,
        has_model as _has_model,
    )
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False
    def _ai_unavailable(*_args, **_kwargs):
        raise HTTPException(status_code=503, detail="AI categorizer unavailable. Install scikit-learn and train a model.")
    _train_categorizer = _ai_unavailable
    _predict_categorizer = _ai_unavailable
    def _has_model(_user_id: str) -> bool:
        return False


app = FastAPI(title="Smart Financial Coach API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    db_mod.init_db()


# CORS for local Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "Smart Financial Coach API",
        "status": "ok",
        "endpoints": [
            "/health",
            "/ingest/csv",
            "/users/{user_id}/transactions",
            "/categorization/explain",
        ],
    }


@app.get("/health", tags=["meta"])
def health():
    # Basic DB connectivity check
    try:
        with db_mod.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"db_error: {e}")
    return {"status": "healthy"}


@app.post("/ingest/csv", tags=["ingestion"])
async def ingest_csv(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    default_account_id: Optional[str] = Form(None),
):
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/csv"):
        # Allow anyway, as some browsers send application/octet-stream for CSV
        pass

    content = await file.read()
    try:
        records = parse_csv_transactions(content, user_id=user_id, default_account_id=default_account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"parse_error: {e}")

    if not records:
        return {"inserted": 0, "skipped": 0, "total_rows": 0}

    inserted = 0
    skipped = 0
    seen_hashes = set()
    with db_mod.get_connection() as conn:
        # Ensure user exists
        conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))

        # Ensure default account exists if provided
        if default_account_id:
            conn.execute(
                "INSERT OR IGNORE INTO accounts (id, user_id, name, type, institution, mask) VALUES (?, ?, ?, ?, ?, ?)",
                (default_account_id, user_id, "Default Account", None, None, None),
            )

        # Ensure any referenced accounts exist
        for r in records:
            acc_id = r.get("account_id")
            if acc_id:
                conn.execute(
                    "INSERT OR IGNORE INTO accounts (id, user_id, name, type, institution, mask) VALUES (?, ?, ?, ?, ?, ?)",
                    (acc_id, user_id, r.get("account_name") or "Imported", None, None, None),
                )

        for r in records:
            # Duplicate detection: hash(date, amount, merchant) per user
            h = dupe_hash(user_id, r["date"], r["amount"], r.get("merchant"))
            if h in seen_hashes:
                skipped += 1
                continue

            # Check DB for existing row with same key
            merchant_norm = (r.get("merchant") or "").strip().lower()
            amount_cents = int(round(float(r["amount"]) * 100))
            exists = conn.execute(
                """
                SELECT 1 FROM transactions
                WHERE user_id = ? AND date = ?
                  AND CAST(ROUND(amount * 100) AS INTEGER) = ?
                  AND LOWER(COALESCE(merchant, '')) = ?
                LIMIT 1
                """,
                (user_id, r["date"], amount_cents, merchant_norm),
            ).fetchone()

            if exists:
                skipped += 1
                continue

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO transactions (
                        id, user_id, account_id, date, amount, merchant, description,
                        category, category_source, category_provenance,
                        is_recurring, mcc, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["id"], r["user_id"], r.get("account_id"), r["date"], r["amount"], r.get("merchant"),
                        r.get("description"), r.get("category"), r.get("category_source"), r.get("category_provenance"),
                        r.get("is_recurring", False), r.get("mcc"), r.get("source", "csv"),
                    ),
                )
                if conn.total_changes > 0:
                    inserted += 1
                    seen_hashes.add(h)
                else:
                    skipped += 1
            except Exception:
                skipped += 1

    sample = records[0] if records else None
    # Hide possibly verbose fields in sample
    if sample and "raw" in sample:
        sample.pop("raw", None)

    return {
        "inserted": inserted,
        "skipped": skipped,
        "total_rows": len(records),
        "sample": sample,
    }


@app.get("/users/{user_id}/transactions", tags=["transactions"])
def list_transactions(user_id: str, limit: int = Query(50, ge=1, le=500)):
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, date, amount, merchant, description, category, category_source, category_provenance,
                   is_recurring, mcc, account_id
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/categorization/explain", tags=["categorization"])
def categorization_explain(
    merchant: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    mcc: Optional[str] = Query(None),
):
    category, source, prov, rule = categorize_with_provenance(merchant, description, mcc, None)
    return {
        "input": {"merchant": merchant, "description": description, "mcc": mcc},
        "category": category,
        "category_source": source,
        "category_provenance": prov,
        "rule": rule,
    }


class DetectRequest(BaseModel):
    user_id: str


@app.post("/subscriptions/detect", tags=["subscriptions"])
def subscriptions_detect(body: DetectRequest):
    with db_mod.get_connection() as conn:
        subs = detect_subscriptions_for_user(conn, body.user_id)
        inserted, updated = upsert_subscriptions(conn, body.user_id, subs)
    return {
        "user_id": body.user_id,
        "detected": len(subs),
        "inserted": inserted,
        "updated": updated,
        "sample": subs[0].__dict__ if subs else None,
    }


@app.get("/users/{user_id}/subscriptions", tags=["subscriptions"])
def list_subscriptions(user_id: str, limit: int = Query(100, ge=1, le=500)):
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT merchant, avg_amount, cadence, last_seen, status, price_change_pct
            FROM subscriptions
            WHERE user_id = ?
            ORDER BY avg_amount DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


class CategorizationRequest(BaseModel):
    merchant: Optional[str] = None
    description: Optional[str] = None
    mcc: Optional[str] = None


@app.post("/categorization/explain", tags=["categorization"])
def categorization_explain_post(body: CategorizationRequest):
    category, source, prov, rule = categorize_with_provenance(
        body.merchant, body.description, body.mcc, None
    )
    return {
        "input": {"merchant": body.merchant, "description": body.description, "mcc": body.mcc},
        "category": category,
        "category_source": source,
        "category_provenance": prov,
        "rule": rule,
    }


# Insights
class InsightsGenerateRequest(BaseModel):
    user_id: str


@app.post("/insights/generate", tags=["insights"])
def insights_generate(body: InsightsGenerateRequest):
    with db_mod.get_connection() as conn:
        items = generate_insights(conn, body.user_id)
        upsert_insights(conn, items)
    return {"user_id": body.user_id, "count": len(items), "sample": items[0] if items else None}


@app.get("/users/{user_id}/insights", tags=["insights"])
def list_insights(user_id: str, limit: int = Query(50, ge=1, le=200)):
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, type, title, body, severity, data_json, created_at
            FROM insights
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            out.append(dict(r))
        return out


# AI Categorizer endpoints
class TrainCategorizerRequest(BaseModel):
    user_id: str
    min_per_class: int | None = 5


@app.post("/ai/categorizer/train", tags=["ai"])
def ai_categorizer_train(body: TrainCategorizerRequest):
    with db_mod.get_connection() as conn:
        try:
            info = _train_categorizer(conn, body.user_id, min_per_class=body.min_per_class or 5)
            # Convert Counter to dict if present
            counts = info.get("counts")
            if counts is not None and hasattr(counts, "items"):
                info["counts"] = {k: int(v) for k, v in counts.items()}
            return info
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


class PredictCategorizerRequest(BaseModel):
    user_id: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    top_k: Optional[int] = 3


@app.post("/ai/categorizer/predict", tags=["ai"])
def ai_categorizer_predict(body: PredictCategorizerRequest):
    try:
        return _predict_categorizer(body.user_id, body.merchant, body.description, top_k=body.top_k or 3)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Plaid endpoints
class LinkTokenRequest(BaseModel):
    user_id: str


@app.post("/plaid/link/token/create", tags=["plaid"])
def plaid_link_token_create(body: LinkTokenRequest):
    try:
        return _create_link_token(body.user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# IsolationForest anomaly (ML)
class IForestDetectRequest(BaseModel):
    user_id: str
    contamination: float | None = 0.08


@app.post("/anomaly/iforest/detect", tags=["ai"])
def iforest_detect(body: IForestDetectRequest):
    with db_mod.get_connection() as conn:
        items = detect_iforest_insights(conn, body.user_id, contamination=body.contamination or 0.08)
        if items:
            upsert_insights(conn, items)
    return {"user_id": body.user_id, "count": len(items) if items else 0, "sample": items[0] if items else None}


# Forecast categories for next month
class ForecastRequest(BaseModel):
    user_id: str
    months_history: int | None = 6
    top_k: int | None = 8


@app.post("/forecast/categories", tags=["forecast"])
def categories_forecast(body: ForecastRequest):
    with db_mod.get_connection() as conn:
        out = forecast_categories(conn, body.user_id, months_history=body.months_history or 6, top_k=body.top_k or 8)
    return out


# LLM rewrite of insights
class RewriteInsightRequest(BaseModel):
    user_id: str
    insight_id: str
    tone: str | None = None


@app.post("/insights/rewrite", tags=["ai"])
def insights_rewrite(body: RewriteInsightRequest):
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM unavailable. Set OPENAI_API_KEY and install dependencies.")
    with db_mod.get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, body, data_json FROM insights WHERE user_id = ? AND id = ?",
            (body.user_id, body.insight_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="insight_not_found")
        new_text = rewrite_insight_llm(row["title"], row["body"], row["data_json"], tone=body.tone)
    return {"insight_id": body.insight_id, "rewritten": new_text}


class PublicTokenExchangeRequest(BaseModel):
    user_id: str
    public_token: str


@app.post("/plaid/link/public_token/exchange", tags=["plaid"])
def plaid_public_token_exchange(body: PublicTokenExchangeRequest):
    try:
        return _exchange_public_token(body.user_id, body.public_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class PlaidImportRequest(BaseModel):
    user_id: str
    start_date: str | None = None
    end_date: str | None = None


@app.post("/plaid/transactions/import", tags=["plaid"])
def plaid_transactions_import(body: PlaidImportRequest):
    try:
        return _import_transactions_for_user(body.user_id, body.start_date, body.end_date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
