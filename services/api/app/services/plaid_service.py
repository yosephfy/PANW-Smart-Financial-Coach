from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3

try:
    from ..plaid_integration import (
        create_link_token as _create_link_token,
        exchange_public_token as _exchange_public_token,
        import_transactions_for_user as _import_transactions_for_user,
    )
except Exception as e:  # pragma: no cover
    _create_link_token = None
    _exchange_public_token = None
    _import_transactions_for_user = None


def create_link_token(user_id: str) -> Dict:
    if _create_link_token is None:
        raise RuntimeError("Plaid integration unavailable")
    return _create_link_token(user_id)


def exchange_public_token(user_id: str, public_token: str) -> Dict:
    if _exchange_public_token is None:
        raise RuntimeError("Plaid integration unavailable")
    return _exchange_public_token(user_id, public_token)


def import_transactions(user_id: str, start_date: Optional[str], end_date: Optional[str]) -> Dict:
    if _import_transactions_for_user is None:
        raise RuntimeError("Plaid integration unavailable")
    return _import_transactions_for_user(user_id, start_date, end_date)


def list_items(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    rows = conn.execute(
        "SELECT item_id, institution_name, created_at FROM plaid_items WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_item(conn: sqlite3.Connection, user_id: str, item_id: str) -> int:
    cur = conn.execute("DELETE FROM plaid_items WHERE user_id = ? AND item_id = ?", (user_id, item_id))
    return cur.rowcount

