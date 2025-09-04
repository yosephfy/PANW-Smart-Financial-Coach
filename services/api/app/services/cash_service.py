from __future__ import annotations

from typing import Dict, Optional
import sqlite3


def _current_balances(conn: sqlite3.Connection, user_id: str, account_id: Optional[str] = None) -> Dict[str, float]:
    if account_id:
        row = conn.execute(
            """
            SELECT balance FROM transactions
            WHERE user_id = ? AND account_id = ? AND balance IS NOT NULL
            ORDER BY date DESC LIMIT 1
            """,
            (user_id, account_id),
        ).fetchone()
        bal = float(row["balance"]) if row and row["balance"] is not None else 0.0
        return {account_id: bal}
    # latest balance per account
    rows = conn.execute(
        """
        SELECT t.account_id, t.balance
        FROM transactions t
        JOIN (
          SELECT account_id, MAX(date) AS md
          FROM transactions WHERE user_id = ? AND balance IS NOT NULL GROUP BY account_id
        ) x ON x.account_id = t.account_id AND x.md = t.date
        WHERE t.user_id = ? AND t.balance IS NOT NULL
        """,
        (user_id, user_id),
    ).fetchall()
    out: Dict[str, float] = {}
    for r in rows:
        acc = r["account_id"] or ""
        out[acc] = float(r["balance"]) if r["balance"] is not None else 0.0
    return out


def _avg_daily_spend(conn: sqlite3.Connection, user_id: str, lookback_days: int = 30) -> float:
    row = conn.execute(
        """
        SELECT SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS spend
        FROM transactions WHERE user_id = ? AND date >= DATE('now', ?)
        """,
        (user_id, f"-{lookback_days} day"),
    ).fetchone()
    total = float(row["spend"] or 0.0)
    return total / float(lookback_days)


def _per_day_recurring(conn: sqlite3.Connection, user_id: str) -> float:
    rows = conn.execute(
        "SELECT cadence, avg_amount FROM subscriptions WHERE user_id = ? AND status = 'active'",
        (user_id,),
    ).fetchall()
    per_day = 0.0
    for r in rows:
        cad = (r["cadence"] or "").lower()
        amt = abs(float(r["avg_amount"] or 0.0))
        if cad == "weekly":
            per_day += amt / 7.0
        elif cad == "monthly":
            per_day += amt / 30.0
        elif cad == "yearly":
            per_day += amt / 365.0
    return per_day


def safe_to_spend(conn: sqlite3.Connection, user_id: str, account_id: Optional[str] = None, days: int = 14, buffer: float = 100.0) -> Dict:
    bals = _current_balances(conn, user_id, account_id)
    current_balance = sum(bals.values())
    avg_spend = _avg_daily_spend(conn, user_id, 30)
    per_day_rec = _per_day_recurring(conn, user_id)
    expected_spend = avg_spend * days
    expected_recurring = per_day_rec * days
    sts = current_balance - (expected_spend + expected_recurring + buffer)
    return {
        "user_id": user_id,
        "account_id": account_id,
        "days": days,
        "current_balance": round(current_balance, 2),
        "avg_daily_spend": round(avg_spend, 2),
        "per_day_recurring": round(per_day_rec, 2),
        "expected_spend": round(expected_spend, 2),
        "expected_recurring": round(expected_recurring, 2),
        "buffer": buffer,
        "safe_to_spend": round(sts, 2),
    }


def low_balance_check(conn: sqlite3.Connection, user_id: str, threshold: float = 100.0, lookback_days: int = 30) -> Dict:
    rows = conn.execute(
        """
        SELECT date, account_id, balance FROM transactions
        WHERE user_id = ? AND balance IS NOT NULL AND date >= DATE('now', ?)
          AND balance < ?
        ORDER BY date DESC
        """,
        (user_id, f"-{lookback_days} day", threshold),
    ).fetchall()
    alerts = [
        {"date": r["date"], "account_id": r["account_id"], "balance": float(r["balance"])}
        for r in rows
    ]
    return {"user_id": user_id, "threshold": threshold, "count": len(alerts), "alerts": alerts}

