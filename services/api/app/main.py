from .api import plaid as plaid_router
from .api import anomaly as anomaly_router
from .api import forecast as forecast_router
from .api import ai as ai_router
from .api import categorization as categorization_router
from .api import goals as goals_router
from .api import subscriptions as subscriptions_router
from .api import insights as insights_router
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from . import db as db_mod
from .ingest import parse_csv_transactions
from pydantic import BaseModel
from .services.ingestion_service import ingest_records as _ingest_records, AIHooks as _AIHooks, RecHooks as _RecHooks
from .utils import auth as auth_utils
from .insights import generate_insights, upsert_insights
from .repositories import transactions_repo as _txrepo
from .subscriptions import detect_subscriptions_for_user, upsert_subscriptions
from .is_recurring_model import has_model as has_rec_model
try:
    from .is_recurring_model import train_for_user as train_rec_model, predict_for_user as predict_rec_model
    ISREC_AVAILABLE = True
except Exception:
    ISREC_AVAILABLE = False
LLM_AVAILABLE = False

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
        raise HTTPException(
            status_code=503, detail="AI categorizer unavailable. Install scikit-learn and train a model.")
    _train_categorizer = _ai_unavailable
    _predict_categorizer = _ai_unavailable

    def _has_model(_user_id: str) -> bool:
        return False


app = FastAPI(title="Smart Financial Coach API", version="0.1.0")

# Goals: create/list/evaluate


@app.on_event("startup")
def on_startup():
    db_mod.init_db()


# CORS for local Next.js frontend

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include extracted routers
app.include_router(insights_router.router)
app.include_router(subscriptions_router.router)
app.include_router(goals_router.router)
app.include_router(categorization_router.router)
app.include_router(ai_router.router)
app.include_router(forecast_router.router)
app.include_router(anomaly_router.router)
app.include_router(plaid_router.router)

"""
Stateless auth helpers: we use a simple header-based user identity.
Frontend stores the user id after login/register and supplies `X-User-Id`.
"""


def _current_username(request: Request) -> Optional[str]:
    # Prefer explicit header if present (stateless auth)
    header_user = request.headers.get(
        "x-user-id") or request.headers.get("x-user")
    if header_user:
        return header_user.strip()
    return None


def _current_user(request: Request, provided: Optional[str] = None) -> Optional[str]:
    # Stateless: header takes precedence, then explicit provided param
    header_user = request.headers.get(
        "x-user-id") or request.headers.get("x-user")
    if header_user:
        return header_user.strip()
    if provided:
        return provided
    return None


def _set_session(resp: Response, username: str):
    # No-op in stateless mode; kept for compatibility
    return


def _clear_session(resp: Response):
    # No-op in stateless mode; kept for compatibility
    return


@app.get("/", tags=["meta"])
def root():
    return {

        "name": "Smart Financial Coach API",
        "status": "ok",
        "endpoints": [
            "/health",
            "/auth/register",
            "/auth/login",
            "/auth/logout",
            "/auth/me",
            "/ingest/csv",
            "/users/{user_id}/transactions",
            "/categorization/explain",
            "/plaid/link/token/create",
            "/plaid/link/public_token/exchange",
            "/plaid/transactions/import",
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


# Auth endpoints
class AuthRequest(BaseModel):
    username: str
    password: str


def _hash_password(password: str, salt: bytes) -> str:
    # Delegate to utils for centralization
    return auth_utils.hash_password(password, salt)


@app.post("/auth/register", tags=["auth"])
def auth_register(body: AuthRequest, response: Response):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="missing_credentials")
    with db_mod.get_connection() as conn:
        # If user exists, error
        exists = conn.execute(
            "SELECT 1 FROM users WHERE id = ?", (username,)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="user_exists")
        import os
        salt = os.urandom(16)
        pwh = _hash_password(body.password, salt)
        conn.execute("INSERT INTO users (id, password_hash, password_salt) VALUES (?, ?, ?)",
                     (username, pwh, salt.hex()))
    # Stateless: return created user id; client stores it and sends X-User-Id
    return {"id": username}


@app.post("/auth/login", tags=["auth"])
def auth_login(body: AuthRequest, response: Response):
    username = body.username.strip()
    with db_mod.get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash, password_salt FROM users WHERE id = ?", (username,)).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="invalid_credentials")
        salt = bytes.fromhex(row["password_salt"]
                             or "") if row["password_salt"] else b""
        if not salt:
            raise HTTPException(status_code=400, detail="invalid_credentials")
        pwh = _hash_password(body.password, salt)
        if pwh != (row["password_hash"] or ""):
            raise HTTPException(status_code=400, detail="invalid_credentials")
    # Stateless: return user id only
    return {"id": username}


@app.post("/auth/logout", tags=["auth"])
def auth_logout(response: Response):
    _clear_session(response)
    return {"ok": True}


@app.get("/auth/me", tags=["auth"])
def auth_me(request: Request):
    u = _current_username(request)
    if not u:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return {"id": u}


@app.post("/ingest/csv", tags=["ingestion"])
async def ingest_csv(
    request: Request,
    file: UploadFile = File(...),
    default_account_id: Optional[str] = Form(None),
):
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/csv"):
        # Allow anyway, as some browsers send application/octet-stream for CSV
        pass

    # Determine user from header (stateless); CSVs never include user_id
    session_user = _current_user(request)
    if not session_user:
        raise HTTPException(status_code=401, detail="not_authenticated")
    user_id = session_user

    content = await file.read()
    try:
        records = parse_csv_transactions(
            content, user_id=user_id, default_account_id=default_account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"parse_error: {e}")

    # Enforce authenticated user's id on all parsed records
    for r in records:
        r["user_id"] = user_id

    with db_mod.get_connection() as conn:
        ai_hooks = _AIHooks(
            _has_model, _predict_categorizer) if AI_AVAILABLE else None
        rec_hooks = _RecHooks(
            has_rec_model, predict_rec_model) if ISREC_AVAILABLE else None
        result = _ingest_records(
            conn, user_id, records, default_account_id, ai=ai_hooks, rec=rec_hooks)
    return result


@app.post("/ingest/csv/insights", tags=["ingestion"])
async def ingest_csv_with_insights(
    request: Request,
    file: UploadFile = File(...),
    default_account_id: Optional[str] = Form(None),
):
    """Ingest a CSV and immediately generate/upsert insights for the user.

    Returns the ingestion result and the generated insights.
    """
    # Reuse existing ingest implementation
    ingest_result = await ingest_csv(request, file, default_account_id)

    # Generate insights based on the newly-ingested data
    u = _current_username(request)
    if not u:
        raise HTTPException(status_code=401, detail="not_authenticated")
    with db_mod.get_connection() as conn:
        items = generate_insights(conn, u)
        if items:
            upsert_insights(conn, items)

        # Detect subscriptions from the newly-ingested transactions and upsert
        try:
            subs = detect_subscriptions_for_user(conn, u)
            inserted, updated = upsert_subscriptions(conn, u, subs)
            # Convert dataclass objects to serializable dicts
            subs_list = [s.__dict__ for s in subs]
            subs_summary = {
                "detected": len(subs_list),
                "inserted": inserted,
                "updated": updated,
                "sample": subs_list[0] if subs_list else None,
                "items": subs_list,
            }
        except Exception:
            subs_summary = {"error": "subscription_detection_failed"}

    return {"ingest": ingest_result, "insights": items, "subscriptions": subs_summary}


@app.get("/users/{user_id}/transactions", tags=["transactions"])
def list_transactions(user_id: str, limit: int = Query(50, ge=1, le=500)):
    with db_mod.get_connection() as conn:
        return _txrepo.list_recent(conn, user_id, limit)


@app.get("/me/transactions", tags=["transactions"])
def list_transactions_me(request: Request, limit: int = Query(50, ge=1, le=500)):
    u = _current_username(request)
    if not u:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return list_transactions(u, limit)


class UserCreateRequest(BaseModel):
    user_id: str


@app.post("/users", tags=["users"])
def create_user(body: UserCreateRequest):
    """Create a user (id provided). No password — lightweight for demo use."""
    with db_mod.get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (id) VALUES (?)", (body.user_id,))
    return {"user_id": body.user_id, "created": True}


@app.get("/users", tags=["users"])
def list_users():
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, created_at FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


class TransactionCreateRequest(BaseModel):
    date: str
    amount: float
    merchant: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[str] = None
    category: Optional[str] = None
    is_recurring: Optional[bool] = False
    mcc: Optional[str] = None
    source: Optional[str] = "manual"


@app.post("/users/{user_id}/transactions", tags=["transactions"])
def create_transaction(user_id: str, body: TransactionCreateRequest, request: Request):
    """Insert a single transaction for a user (used by "Add transaction" UI).

    This follows the same insertion rules as CSV ingest: ensures accounts exist,
    applies ML categorization fallback when available, and returns the inserted row on success.
    """
    import uuid

    # Enforce that caller is the same user (stateless header auth)
    u = _current_username(request)
    if not u or u != user_id:
        raise HTTPException(status_code=401, detail="not_authenticated")

    tid = uuid.uuid4().hex
    with db_mod.get_connection() as conn:
        # ensure user exists
        conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))

        # ensure account exists if provided
        if body.account_id:
            conn.execute(
                "INSERT OR IGNORE INTO accounts (id, user_id, name, type, institution, mask) VALUES (?, ?, ?, ?, ?, ?)",
                (body.account_id, user_id, "Manual", None, None, None),
            )

        # prepare row dict for possible ML categorization
        row = {
            "id": tid,
            "user_id": user_id,
            "account_id": body.account_id,
            "date": body.date,
            "amount": body.amount,
            "merchant": body.merchant,
            "description": body.description,
            "category": body.category,
            "category_source": None,
            "category_provenance": None,
            "is_recurring": bool(body.is_recurring),
            "mcc": body.mcc,
            "source": body.source or "manual",
        }

        # ML fallback
        if AI_AVAILABLE and _has_model(user_id) and not row.get("category"):
            try:
                pred = _predict_categorizer(user_id, row.get(
                    "merchant"), row.get("description"))
                preds = pred.get("predictions", [])
                if preds:
                    top = preds[0]
                    if float(top.get("prob", 0)) >= 0.7:
                        row["category"] = top["label"]
                        row["category_source"] = "ml"
                        row["category_provenance"] = f"ml:{top['label']}:{float(top['prob']):.2f}"
            except Exception:
                pass

        try:
            conn.execute(
                """
                INSERT INTO transactions (id, user_id, account_id, date, amount, merchant, description,
                    category, category_source, category_provenance, is_recurring, mcc, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"], row["user_id"], row.get(
                        "account_id"), row["date"], row["amount"],
                    row.get("merchant"), row.get("description"), row.get(
                        "category"), row.get("category_source"),
                    row.get("category_provenance"), int(
                        bool(row.get("is_recurring", False))), row.get("mcc"), row.get("source"),
                ),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"insert_error: {e}")

    return {"inserted": True, "transaction": row}


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


class TrainRecurringRequest(BaseModel):
    user_id: str


@app.post("/ai/is_recurring/train", tags=["ai"])
def api_is_recurring_train(body: TrainRecurringRequest):
    with db_mod.get_connection() as conn:
        try:
            # Ensure subscriptions table is up to date for labels
            subs = detect_subscriptions_for_user(conn, body.user_id)
            upsert_subscriptions(conn, body.user_id, subs)
            info = train_rec_model(conn, body.user_id)
            return info
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


class PredictRecurringRequest(BaseModel):
    user_id: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    amount: float
    date: str


@app.post("/ai/is_recurring/predict", tags=["ai"])
def api_is_recurring_predict(body: PredictRecurringRequest):
    try:
        return predict_rec_model(body.user_id, body.merchant, body.description, body.amount, body.date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
