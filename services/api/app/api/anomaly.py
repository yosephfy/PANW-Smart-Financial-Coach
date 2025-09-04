from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db as db_mod
from ..services import anomaly_service as svc


router = APIRouter(tags=["ai"])


class IForestDetectRequest(BaseModel):
    user_id: str
    contamination: float | None = 0.08


@router.post("/anomaly/iforest/detect")
def iforest_detect(body: IForestDetectRequest):
    with db_mod.get_connection() as conn:
        return svc.iforest_detect(conn, body.user_id, contamination=body.contamination or 0.08)

