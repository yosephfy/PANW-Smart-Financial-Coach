from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .. import db as db_mod
from ..services import ai_service as svc


router = APIRouter(tags=["ai"])


class TrainCategorizerRequest(BaseModel):
    user_id: str
    min_per_class: int | None = 5


@router.post("/ai/categorizer/train")
def ai_categorizer_train(body: TrainCategorizerRequest):
    with db_mod.get_connection() as conn:
        try:
            return svc.train_categorizer(conn, body.user_id, min_per_class=body.min_per_class or 5)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


class PredictCategorizerRequest(BaseModel):
    user_id: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    top_k: Optional[int] = 3


@router.post("/ai/categorizer/predict")
def ai_categorizer_predict(body: PredictCategorizerRequest):
    try:
        return svc.predict_categorizer(body.user_id, body.merchant, body.description, top_k=body.top_k or 3)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

