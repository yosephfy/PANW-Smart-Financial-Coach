from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from ..ingest import categorize_with_provenance


router = APIRouter(tags=["categorization"])


class CategorizationRequest(BaseModel):
    merchant: Optional[str] = None
    description: Optional[str] = None
    mcc: Optional[str] = None


@router.post("/categorization/explain")
def categorization_explain_post(body: CategorizationRequest):
    category, source, prov, rule = categorize_with_provenance(
        body.merchant, body.description, body.mcc, None
    )
    return {
        "input": {"merchant": body.merchant, "description": body.description, "mcc": body.mcc},
        "category": category,
        "category_source": source,
        "category_provenance": prov,
        "rule": rule,
    }


@router.get("/categorization/explain")
def categorization_explain(
    merchant: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    mcc: Optional[str] = Query(None),
):
    category, source, prov, rule = categorize_with_provenance(
        merchant, description, mcc, None)
    return {
        "input": {"merchant": merchant, "description": description, "mcc": mcc},
        "category": category,
        "category_source": source,
        "category_provenance": prov,
        "rule": rule,
    }

