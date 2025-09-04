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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"llm_error: {e}")
