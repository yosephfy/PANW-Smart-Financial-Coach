from __future__ import annotations

from typing import Dict, Optional
import sqlite3
from datetime import date, timedelta
from ..utils.account_utils import get_account_balances_by_type, get_low_balance_accounts, get_account_threshold


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
        bal = float(
            row["balance"]) if row and row["balance"] is not None else 0.0
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
    def _income_dates(u: str):
        rows = conn.execute(
            """
            SELECT date, amount, COALESCE(LOWER(category),'') as cat, COALESCE(LOWER(merchant),'') as m
            FROM transactions WHERE user_id = ? AND amount > 0
            ORDER BY date ASC
            """,
            (u,),
        ).fetchall()
        return [date.fromisoformat(r["date"]) for r in rows if abs(float(r["amount"])) >= 50.0]

    def _estimate_pay_cycle(u: str):
        ds = _income_dates(u)
        if len(ds) < 2:
            return None, 14  # default 14 days
        gaps = [(ds[i] - ds[i-1]).days for i in range(1, len(ds))
                if (ds[i] - ds[i-1]).days > 0]
        if not gaps:
            return None, 14
        # choose closest to 14 or 30
        cand = min(gaps, key=lambda g: min(abs(g-14), abs(g-30)))
        cycle = 14 if abs(cand-14) <= abs(cand-30) else 30
        last = ds[-1]
        today = date.today()
        next_pay = last
        while next_pay <= today:
            next_pay = next_pay + timedelta(days=cycle)
        return next_pay, cycle

    bals = _current_balances(conn, user_id, account_id)
    current_balance = sum(bals.values())
    avg_spend = _avg_daily_spend(conn, user_id, 30)
    per_day_rec = _per_day_recurring(conn, user_id)

    next_pay_date, cycle_days = _estimate_pay_cycle(user_id)
    today = date.today()
    days_to_pay = (next_pay_date - today).days if next_pay_date else days

    expected_spend = avg_spend * days
    expected_recurring = per_day_rec * days
    sts = current_balance - (expected_spend + expected_recurring + buffer)

    exp_spend_until_pay = avg_spend * days_to_pay
    exp_rec_until_pay = per_day_rec * days_to_pay
    sts_until_pay = current_balance - \
        (exp_spend_until_pay + exp_rec_until_pay + buffer)
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
        "next_pay_date": next_pay_date.isoformat() if next_pay_date else None,
        "days_to_pay": days_to_pay,
        "safe_to_spend_until_pay": round(sts_until_pay, 2),
    }


def safe_to_spend_by_account_type(conn: sqlite3.Connection, user_id: str, days: int = 14) -> Dict:
    """
    Calculate safe-to-spend with account type awareness.
    Different thresholds for checking vs credit accounts.
    """
    print(f"[DEBUG] safe_to_spend_by_account_type called for user: {user_id}")

    account_data = get_account_balances_by_type(conn, user_id)
    print(f"[DEBUG] Account data from utils: {account_data}")

    avg_spend = _avg_daily_spend(conn, user_id, 30)
    per_day_rec = _per_day_recurring(conn, user_id)

    next_pay_date, cycle_days = _estimate_pay_cycle(conn, user_id)
    today = date.today()
    days_to_pay = (next_pay_date - today).days if next_pay_date else days

    expected_spend = avg_spend * days
    expected_recurring = per_day_rec * days

    # Calculate safe-to-spend for each account type
    checking_data = account_data["checking"]
    credit_data = account_data["credit"]

    print(f"[DEBUG] Checking data: {checking_data}")
    print(f"[DEBUG] Credit data: {credit_data}")

    # For checking accounts, use conservative buffer (100)
    checking_buffer = 100.0
    checking_sts = checking_data["total"] - \
        (expected_spend + expected_recurring + checking_buffer)

    # For credit accounts, use different logic (available credit)
    # Assume credit limit is roughly where they've maxed out historically + some buffer
    credit_buffer = 200.0  # More conservative for credit
    # Credit balance is negative, so this shows available spend
    credit_sts = credit_data["total"] - credit_buffer

    # Combined safe to spend (more conservative)
    combined_sts = min(checking_sts, abs(credit_sts)
                       ) if credit_data["count"] > 0 else checking_sts

    return {
        "user_id": user_id,
        "days": days,
        "checking": {
            "total": checking_data["total"],
            "count": checking_data["count"],
            "accounts": checking_data["accounts"],
            "safe_to_spend": round(checking_sts, 2),
            "buffer": checking_buffer
        },
        "credit": {
            "total": credit_data["total"],
            "count": credit_data["count"],
            "accounts": credit_data["accounts"],
            "available_credit": round(abs(credit_sts), 2),
            "buffer": credit_buffer
        },
        "combined": {
            "net_worth": account_data["net_worth"],
            "safe_to_spend": round(combined_sts, 2),
            "avg_daily_spend": round(avg_spend, 2),
            "per_day_recurring": round(per_day_rec, 2),
            "expected_spend": round(expected_spend, 2),
            "expected_recurring": round(expected_recurring, 2)
        },
        "next_pay_date": next_pay_date.isoformat() if next_pay_date else None,
        "days_to_pay": days_to_pay,
    }


def _estimate_pay_cycle(conn: sqlite3.Connection, user_id: str):
    """Helper function to estimate pay cycle"""
    def _income_dates(u: str):
        rows = conn.execute(
            """
            SELECT date, amount, COALESCE(LOWER(category),'') as cat, COALESCE(LOWER(merchant),'') as m
            FROM transactions WHERE user_id = ? AND amount > 0
            ORDER BY date ASC
            """,
            (u,),
        ).fetchall()
        return [date.fromisoformat(r["date"]) for r in rows if abs(float(r["amount"])) >= 50.0]

    ds = _income_dates(user_id)
    if len(ds) < 2:
        return None, 14  # default 14 days
    gaps = [(ds[i] - ds[i-1]).days for i in range(1, len(ds))
            if (ds[i] - ds[i-1]).days > 0]
    if not gaps:
        return None, 14
    # choose closest to 14 or 30
    cand = min(gaps, key=lambda g: min(abs(g-14), abs(g-30)))
    cycle = 14 if abs(cand-14) <= abs(cand-30) else 30
    last = ds[-1]
    today = date.today()
    next_pay = last
    while next_pay <= today:
        next_pay = next_pay + timedelta(days=cycle)
    return next_pay, cycle


def low_balance_check(conn: sqlite3.Connection, user_id: str, lookback_days: int = 30) -> Dict:
    """
    Check for low balances using account type-specific thresholds.
    """
    low_accounts = get_low_balance_accounts(conn, user_id, lookback_days)

    return {
        "user_id": user_id,
        "lookback_days": lookback_days,
        "count": len(low_accounts),
        "alerts": low_accounts
    }


def upcoming_bills(conn: sqlite3.Connection, user_id: str, days: int = 14) -> Dict:
    today = date.today()
    end = today + timedelta(days=days)
    rows = conn.execute(
        "SELECT merchant, cadence, last_seen, abs(avg_amount) as amt FROM subscriptions WHERE user_id = ? AND status = 'active'",
        (user_id,),
    ).fetchall()
    items = []
    total = 0.0
    for r in rows:
        cad = (r["cadence"] or "").lower()
        last = r["last_seen"]
        try:
            last_d = date.fromisoformat(last) if last else today
        except Exception:
            last_d = today
        step = 30
        if cad == "weekly":
            step = 7
        elif cad == "monthly":
            step = 30
        elif cad == "yearly":
            step = 365
        # roll forward to next due
        due = last_d
        while due <= today:
            due = due + timedelta(days=step)
        if due <= end:
            amt = float(r["amt"] or 0.0)
            items.append({
                "merchant": r["merchant"],
                "due_date": due.isoformat(),
                "amount": amt,
                "cadence": cad,
            })
            total += amt
    return {"user_id": user_id, "days": days, "total_due": round(total, 2), "items": items}
