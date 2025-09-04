from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .. import db as db_mod
from ..services import forecast_service as svc


router = APIRouter(tags=["forecast"])


class ForecastRequest(BaseModel):
    user_id: str
    months_history: int | None = 6
    top_k: int | None = 8


@router.post("/forecast/categories")
def categories_forecast(body: ForecastRequest):
    with db_mod.get_connection() as conn:
        return svc.categories_forecast(conn, body.user_id, months_history=body.months_history or 6, top_k=body.top_k or 8)

