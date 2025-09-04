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


class AccountTypeSTSRequest(BaseModel):
    user_id: str
    days: Optional[int] = 14


@router.post("/cash/safe_to_spend_by_account_type")
def api_safe_to_spend_by_account_type(body: AccountTypeSTSRequest):
    """Get safe-to-spend analysis with account type awareness (checking vs credit)."""
    with db_mod.get_connection() as conn:
        return svc.safe_to_spend_by_account_type(conn, body.user_id, body.days or 14)


class LowBalanceRequest(BaseModel):
    user_id: str
    lookback_days: Optional[int] = 30


@router.post("/cash/low_balance/check")
def api_low_balance(body: LowBalanceRequest):
    """Check for accounts with low balances using account type-specific thresholds."""
    with db_mod.get_connection() as conn:
        return svc.low_balance_check(conn, body.user_id, body.lookback_days or 30)


class UpcomingBillsRequest(BaseModel):
    user_id: str
    days: int | None = 14


@router.post("/cash/upcoming_bills")
def api_upcoming_bills(body: UpcomingBillsRequest):
    with db_mod.get_connection() as conn:
        return svc.upcoming_bills(conn, body.user_id, body.days or 14)
