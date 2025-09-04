from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from .. import db as db_mod
from ..utils.auth import current_username
from ..services import insights_service as svc


router = APIRouter(tags=["insights"])


class InsightsGenerateRequest(BaseModel):
    user_id: str


@router.post("/insights/generate")
def insights_generate(body: InsightsGenerateRequest):
    with db_mod.get_connection() as conn:
        items = svc.generate_and_upsert(conn, body.user_id)
    return {"user_id": body.user_id, "count": len(items), "sample": items[0] if items else None}


# Removed cookie-based "me" route; use /insights/generate with body { user_id }


@router.get("/users/{user_id}/insights")
def list_insights(user_id: str, limit: int = Query(50, ge=1, le=200)):
    with db_mod.get_connection() as conn:
        return svc.list_for_user(conn, user_id, limit)


# Removed cookie-based "me" route; use /users/{user_id}/insights


class RewriteInsightRequest(BaseModel):
    user_id: str
    insight_id: str
    tone: str | None = None


@router.post("/insights/rewrite", tags=["ai"])
def insights_rewrite(body: RewriteInsightRequest):
    try:
        with db_mod.get_connection() as conn:
            return svc.rewrite(conn, body.user_id, body.insight_id, body.tone)
    except KeyError:
        raise HTTPException(status_code=404, detail="insight_not_found")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


class TransactionInsightsRequest(BaseModel):
    user_id: str
    transaction_id: str


@router.post("/insights/transaction/generate")
def generate_transaction_insights(body: TransactionInsightsRequest):
    """Generate insights for a specific transaction."""
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

        # Convert to dict
        transaction = dict(tx)

        # Generate insights
        items = svc.generate_transaction_insights_and_upsert(
            conn, body.user_id, transaction)

    return {"user_id": body.user_id, "transaction_id": body.transaction_id, "count": len(items), "insights": items}


@router.get("/users/{user_id}/transactions/{transaction_id}/insights")
def list_transaction_insights(user_id: str, transaction_id: str):
    """List insights for a specific transaction."""
    with db_mod.get_connection() as conn:
        return svc.list_for_user_by_transaction(conn, user_id, transaction_id)


@router.post("/insights/transaction/subscription")
def check_transaction_subscription_impact(body: TransactionInsightsRequest):
    """Check if a transaction affects subscription detection."""
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

        # Check subscription impact
        from ..services.transaction_subscription_service import detect_transaction_subscription_updates
        subscription_update = detect_transaction_subscription_updates(
            conn, body.user_id, dict(tx))

        return {
            "user_id": body.user_id,
            "transaction_id": body.transaction_id,
            "subscription_update": subscription_update
        }
