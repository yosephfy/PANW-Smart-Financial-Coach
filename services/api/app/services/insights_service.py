from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3
import time

from ..insights import generate_insights, upsert_insights, generate_transaction_insights
from ..insights import (
    generate_duplicate_charge_insights,
    generate_budget_overage_insights,
    generate_budget_suggestion_insights,
    generate_low_balance_insights,
)
from ..services import cash_service as cash
from ..services.llm_service import threaded_llm_service, LLM_AVAILABLE

try:
    from ..llm import rewrite_insight_llm
    LLM_DIRECT_AVAILABLE = True
except Exception:
    LLM_DIRECT_AVAILABLE = False


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
    try:
        items += generate_budget_suggestion_insights(conn, user_id)
    except Exception:
        pass
    try:
        items += generate_low_balance_insights(conn, user_id)
    except Exception:
        pass
    # Upcoming bills coverage insight
    try:
        sts = cash.safe_to_spend(conn, user_id, None, 14, 100.0)
        bills = cash.upcoming_bills(
            conn, user_id, sts.get("days_to_pay", 14) or 14)
        curr = float(sts.get("current_balance", 0.0))
        due = float(bills.get("total_due", 0.0))
        if due > 0:
            covered = curr - due
            sev = "info" if covered >= 0 else "warn"
            title = "Upcoming bills coverage"
            body = f"Bills due ${due:.0f} before next pay; coverage ${covered:.0f}."
            items.append({
                "id": f"bills_coverage|{user_id}",
                "user_id": user_id,
                "type": "bills_coverage",
                "title": title,
                "body": body,
                "severity": sev,
                "data_json": None,
            })
    except Exception:
        pass
    # Rewrite via LLM using threading for better performance
    if items and LLM_AVAILABLE:
        items = threaded_llm_service.rewrite_insights_batch(
            items, tone="friendly")

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
    new_text = rewrite_insight_llm(
        row["title"], row["body"], row["data_json"], tone=tone)
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


def generate_transaction_insights_and_upsert(conn: sqlite3.Connection, user_id: str, transaction: Dict) -> List[Dict]:
    """Generate and upsert insights for a specific transaction with LLM rewrites."""
    items = generate_transaction_insights(conn, user_id, transaction)

    # Apply LLM rewrites if available and items exist
    if items and LLM_AVAILABLE:
        items = threaded_llm_service.rewrite_insights_batch(
            items, tone="friendly")

    if items:
        upsert_insights(conn, items)
    return items


def list_for_user_by_transaction(conn: sqlite3.Connection, user_id: str, transaction_id: str) -> List[Dict]:
    """List insights for a specific user and transaction."""
    rows = conn.execute(
        """
        SELECT id, type, title, body, severity, data_json, created_at,
               rewritten_title, rewritten_body, rewritten_at
        FROM insights
        WHERE user_id = ? AND json_extract(data_json, '$.transaction_id') = ?
        ORDER BY created_at DESC
        """,
        (user_id, transaction_id),
    ).fetchall()
    return [dict(r) for r in rows]
