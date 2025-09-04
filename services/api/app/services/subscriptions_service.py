from __future__ import annotations

from typing import Dict, List
import sqlite3

from ..subscriptions import detect_subscriptions_for_user, upsert_subscriptions


def detect_and_upsert(conn: sqlite3.Connection, user_id: str) -> Dict:
    subs = detect_subscriptions_for_user(conn, user_id)
    inserted, updated = upsert_subscriptions(conn, user_id, subs)
    subs_list = [s.__dict__ for s in subs]
    return {
        "user_id": user_id,
        "detected": len(subs_list),
        "inserted": inserted,
        "updated": updated,
        "sample": subs_list[0] if subs_list else None,
        "items": subs_list,
    }


def list_for_user(conn: sqlite3.Connection, user_id: str, limit: int) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT merchant, avg_amount, cadence, last_seen, status, price_change_pct, COALESCE(trial_converted, 0) as trial_converted
        FROM subscriptions
        WHERE user_id = ?
        ORDER BY avg_amount DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    out: List[Dict] = []
    for r in rows:
        d = dict(r)
        d["trial_converted"] = bool(d.get("trial_converted"))
        out.append(d)
    return out


def update_status(conn: sqlite3.Connection, user_id: str, merchant: str, status: str) -> int:
    cur = conn.execute(
        "UPDATE subscriptions SET status = ? WHERE user_id = ? AND LOWER(merchant) = ?",
        (status, user_id, merchant.strip().lower()),
    )
    return cur.rowcount

