from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from .. import db as db_mod
from ..utils.auth import current_username
from ..services import subscriptions_service as svc


router = APIRouter(tags=["subscriptions"])


class DetectRequest(BaseModel):
    user_id: str | None = None


@router.post("/subscriptions/detect")
def subscriptions_detect(request: Request, body: DetectRequest):
    uid = body.user_id or current_username(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_authenticated")
    with db_mod.get_connection() as conn:
        return svc.detect_and_upsert(conn, uid)


@router.get("/users/{user_id}/subscriptions")
def list_subscriptions(user_id: str, limit: int = Query(100, ge=1, le=500)):
    with db_mod.get_connection() as conn:
        return svc.list_for_user(conn, user_id, limit)


# Removed cookie-based "me" route; use /users/{user_id}/subscriptions


class TransactionSubscriptionRequest(BaseModel):
    user_id: str
    transaction_id: str


@router.post("/subscriptions/transaction/check")
def check_transaction_subscription_impact(body: TransactionSubscriptionRequest):
    """Check if a specific transaction impacts subscription detection."""
    with db_mod.get_connection() as conn:
        # Get the transaction
        tx = conn.execute(
            """
            SELECT id, user_id, account_id, date, amount, merchant, description,
                   category, category_source, category_provenance, is_recurring, mcc, source
            FROM transactions
            WHERE user_id = ? AND id = ?
            """,
            (body.user_id, body.transaction_id),
        ).fetchone()

        if not tx:
            raise HTTPException(
                status_code=404, detail="transaction_not_found")

        from ..services.transaction_subscription_service import detect_transaction_subscription_updates
        return detect_transaction_subscription_updates(conn, body.user_id, dict(tx))


class SubscriptionUpdateRequest(BaseModel):
    status: str
    user_id: str


@router.patch("/subscriptions/{merchant}")
def update_subscription_status(merchant: str, request: Request, body: SubscriptionUpdateRequest):
    u = (body.user_id or "").strip()
    if not u:
        raise HTTPException(status_code=400, detail="missing_user_id")
    status = (body.status or "").strip().lower()
    if status not in {"active", "paused", "canceled"}:
        raise HTTPException(status_code=400, detail="invalid_status")
    with db_mod.get_connection() as conn:
        changed = svc.update_status(conn, u, merchant, status)
        if changed == 0:
            raise HTTPException(
                status_code=404, detail="subscription_not_found")
    return {"merchant": merchant.strip().lower(), "status": status}
