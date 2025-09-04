from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3

from ..insights import generate_insights, upsert_insights
from ..insights import generate_duplicate_charge_insights, generate_budget_overage_insights

try:
    from ..llm import rewrite_insight_llm
    LLM_AVAILABLE = True
except Exception:
    LLM_AVAILABLE = False


def generate_and_upsert(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    items = generate_insights(conn, user_id)
    # Add duplicate charges and budget overage insights
    try:
        items += generate_duplicate_charge_insights(conn, user_id)
    except Exception:
        pass
    try:
        items += generate_budget_overage_insights(conn, user_id)
    except Exception:
        pass
    if items:
        upsert_insights(conn, items)
    return items


def list_for_user(conn: sqlite3.Connection, user_id: str, limit: int) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT id, type, title, body, severity, data_json, created_at,
               rewritten_title, rewritten_body, rewritten_at
        FROM insights
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def rewrite(conn: sqlite3.Connection, user_id: str, insight_id: str, tone: Optional[str] = None) -> Dict:
    if not LLM_AVAILABLE:
        raise RuntimeError("LLM unavailable")
    row = conn.execute(
        "SELECT id, title, body, data_json FROM insights WHERE user_id = ? AND id = ?",
        (user_id, insight_id),
    ).fetchone()
    if not row:
        raise KeyError("insight_not_found")
    new_text = rewrite_insight_llm(row["title"], row["body"], row["data_json"], tone=tone)
    conn.execute(
        """
        UPDATE insights
        SET rewritten_title = ?, rewritten_body = ?, rewritten_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND id = ?
        """,
        (new_text["title"], new_text["body"], user_id, insight_id),
    )
    updated = conn.execute(
        """
        SELECT id, type, title, body, severity, data_json, created_at,
               rewritten_title, rewritten_body, rewritten_at
        FROM insights WHERE user_id = ? AND id = ?
        """,
        (user_id, insight_id),
    ).fetchone()
    return {"insight_id": insight_id, "rewritten": new_text, "insight": dict(updated) if updated else None}
