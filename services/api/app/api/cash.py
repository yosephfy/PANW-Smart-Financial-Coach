from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .. import db as db_mod
from ..services import cash_service as svc


router = APIRouter(tags=["cash"])


class STSRequest(BaseModel):
    user_id: str
    account_id: Optional[str] = None
    days: Optional[int] = 14
    buffer: Optional[float] = 100.0


@router.post("/cash/safe_to_spend")
def api_safe_to_spend(body: STSRequest):
    with db_mod.get_connection() as conn:
        return svc.safe_to_spend(conn, body.user_id, body.account_id, body.days or 14, body.buffer or 100.0)


class LowBalanceRequest(BaseModel):
    user_id: str
    threshold: Optional[float] = 100.0
    lookback_days: Optional[int] = 30


@router.post("/cash/low_balance/check")
def api_low_balance(body: LowBalanceRequest):
    with db_mod.get_connection() as conn:
        return svc.low_balance_check(conn, body.user_id, body.threshold or 100.0, body.lookback_days or 30)

