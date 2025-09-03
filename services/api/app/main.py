from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from . import db as db_mod
from .ingest import parse_csv_transactions, dupe_hash, categorize_with_provenance
from pydantic import BaseModel
from .subscriptions import detect_subscriptions_for_user, upsert_subscriptions


app = FastAPI(title="Smart Financial Coach API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    db_mod.init_db()


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
