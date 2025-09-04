from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from .. import db as db_mod
from ..utils.auth import current_username
from ..services import plaid_service as svc


router = APIRouter(tags=["plaid"])


class LinkTokenRequest(BaseModel):
    user_id: str


@router.post("/plaid/link/token/create")
def plaid_link_token_create(body: LinkTokenRequest):
    try:
        return svc.create_link_token(body.user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plaid/items")
def plaid_items(user_id: str = Query(...)):
    with db_mod.get_connection() as conn:
        return svc.list_items(conn, user_id)


@router.delete("/plaid/items/{item_id}")
def plaid_item_delete(item_id: str, user_id: str = Query(...)):
    with db_mod.get_connection() as conn:
        deleted = svc.delete_item(conn, user_id, item_id)
        return {"deleted": deleted}


class PublicTokenExchangeRequest(BaseModel):
    user_id: str
    public_token: str


@router.post("/plaid/link/public_token/exchange")
def plaid_public_token_exchange(body: PublicTokenExchangeRequest):
    try:
        return svc.exchange_public_token(body.user_id, body.public_token)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class PlaidImportRequest(BaseModel):
    user_id: str
    start_date: str | None = None
    end_date: str | None = None


@router.post("/plaid/transactions/import")
def plaid_transactions_import(body: PlaidImportRequest):
    try:
        return svc.import_transactions(body.user_id, body.start_date, body.end_date)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
