from __future__ import annotations

from typing import Optional, Dict, Any, List
import sqlite3


def ensure_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))


def ensure_account(conn: sqlite3.Connection, account_id: Optional[str], user_id: str, name: Optional[str] = None) -> None:
    if not account_id:
        return
    conn.execute(
        "INSERT OR IGNORE INTO accounts (id, user_id, name, type, institution, mask) VALUES (?, ?, ?, ?, ?, ?)",
        (account_id, user_id, name or "Imported", None, None, None),
    )


def exists_duplicate(conn: sqlite3.Connection, user_id: str, date: str, amount_cents: int, merchant_lower: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM transactions
        WHERE user_id = ? AND date = ?
          AND CAST(ROUND(amount * 100) AS INTEGER) = ?
          AND LOWER(COALESCE(merchant, '')) = ?
        LIMIT 1
        """,
        (user_id, date, amount_cents, merchant_lower),
    ).fetchone()
    return bool(row)


def insert_transaction(conn: sqlite3.Connection, row: Dict[str, Any]) -> bool:
    """Insert a transaction row. Returns True if inserted, False if ignored (duplicate by PK)."""
    pre = conn.total_changes
    conn.execute(
        """
        INSERT OR IGNORE INTO transactions (
            id, user_id, account_id, date, amount, merchant, description,
            category, category_source, category_provenance,
            is_recurring, mcc, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"], row["user_id"], row.get("account_id"), row["date"], row["amount"],
            row.get("merchant"), row.get("description"), row.get("category"), row.get("category_source"),
            row.get("category_provenance"), int(bool(row.get("is_recurring", False))), row.get("mcc"), row.get("source"),
        ),
    )
    return conn.total_changes > pre


def list_recent(conn: sqlite3.Connection, user_id: str, limit: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, date, amount, merchant, description, category, category_source, category_provenance,
               is_recurring, mcc, account_id
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]

