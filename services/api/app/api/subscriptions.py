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


@router.get("/me/subscriptions")
def list_subscriptions_me(request: Request, limit: int = Query(100, ge=1, le=500)):
    u = current_username(request)
    if not u:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return list_subscriptions(u, limit)


class SubscriptionUpdateRequest(BaseModel):
    status: str


@router.patch("/subscriptions/{merchant}")
def update_subscription_status(merchant: str, request: Request, body: SubscriptionUpdateRequest):
    u = current_username(request)
    if not u:
        raise HTTPException(status_code=401, detail="not_authenticated")
    status = (body.status or "").strip().lower()
    if status not in {"active", "paused", "canceled"}:
        raise HTTPException(status_code=400, detail="invalid_status")
    with db_mod.get_connection() as conn:
        changed = svc.update_status(conn, u, merchant, status)
        if changed == 0:
            raise HTTPException(status_code=404, detail="subscription_not_found")
    return {"merchant": merchant.strip().lower(), "status": status}

