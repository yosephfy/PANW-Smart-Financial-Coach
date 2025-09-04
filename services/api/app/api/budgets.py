from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db as db_mod


router = APIRouter(tags=["budgets"])


@router.get("/users/{user_id}/budgets")
def list_budgets(user_id: str):
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            "SELECT category, monthly_budget FROM category_budgets WHERE user_id = ? ORDER BY category",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class BudgetUpsertRequest(BaseModel):
    monthly_budget: float


@router.put("/users/{user_id}/budgets/{category}")
def upsert_budget(user_id: str, category: str, body: BudgetUpsertRequest):
    if body.monthly_budget <= 0:
        raise HTTPException(status_code=400, detail="invalid_budget")
    cat = (category or "").strip().lower()
    with db_mod.get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO category_budgets (user_id, category, monthly_budget) VALUES (?, ?, ?)",
            (user_id, cat, body.monthly_budget),
        )
    return {"user_id": user_id, "category": cat, "monthly_budget": body.monthly_budget}


@router.delete("/users/{user_id}/budgets/{category}")
def delete_budget(user_id: str, category: str):
    cat = (category or "").strip().lower()
    with db_mod.get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM category_budgets WHERE user_id = ? AND category = ?",
            (user_id, cat),
        )
        return {"deleted": cur.rowcount}

