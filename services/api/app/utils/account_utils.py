from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3


def get_account_type(account_id: str) -> str:
    """
    Determine account type based on account_id pattern.
    Returns 'credit' for accounts with '_credit' in the ID, 'checking' otherwise.
    """
    if "_credit" in account_id.lower():
        return "credit"
    return "checking"


def get_account_threshold(account_id: str) -> float:
    """
    Get appropriate balance threshold based on account type.
    Credit cards: -1000 (can go more negative)
    Checking accounts: -100 (should stay positive)
    """
    account_type = get_account_type(account_id)
    if account_type == "credit":
        return -1000.0  # Credit cards can have negative balances (debt)
    return -100.0  # Checking accounts should stay positive


def get_account_balances_by_type(conn: sqlite3.Connection, user_id: str) -> Dict[str, Dict]:
    """
    Get current balances for all accounts, grouped by type with metadata.
    Returns dict with 'checking' and 'credit' keys containing account info.
    """
    print(f"[DEBUG] get_account_balances_by_type called for user: {user_id}")

    # Get latest balance per account
    rows = conn.execute(
        """
        SELECT t.account_id, t.balance, a.name, a.type as account_type_db
        FROM transactions t
        JOIN (
          SELECT account_id, MAX(date) AS md
          FROM transactions WHERE user_id = ? AND balance IS NOT NULL GROUP BY account_id
        ) x ON x.account_id = t.account_id AND x.md = t.date
        LEFT JOIN accounts a ON a.id = t.account_id AND a.user_id = t.user_id
        WHERE t.user_id = ? AND t.balance IS NOT NULL
        """,
        (user_id, user_id),
    ).fetchall()

    print(f"[DEBUG] Raw account rows from database: {len(rows)} rows")
    for i, r in enumerate(rows):
        name_val = r["name"] if r["name"] is not None else "None"
        print(
            f"[DEBUG] Row {i}: account_id={r['account_id']}, balance={r['balance']}, name={name_val}")

    checking_accounts = []
    credit_accounts = []

    for r in rows:
        account_id = r["account_id"] or ""
        balance = float(r["balance"]) if r["balance"] is not None else 0.0
        name = r["name"] or account_id
        account_type = get_account_type(account_id)
        threshold = get_account_threshold(account_id)

        print(
            f"[DEBUG] Processing account: {account_id}, balance: {balance}, type: {account_type}, threshold: {threshold}")

        account_info = {
            "id": account_id,
            "name": name,
            "balance": balance,
            "threshold": threshold,
            "is_low": balance < threshold,
            "type": account_type
        }

        if account_type == "credit":
            credit_accounts.append(account_info)
            print(f"[DEBUG] Added to credit: {account_info}")
        else:
            checking_accounts.append(account_info)
            print(f"[DEBUG] Added to checking: {account_info}")

    # Calculate totals
    checking_total = sum(acc["balance"] for acc in checking_accounts)
    credit_total = sum(acc["balance"] for acc in credit_accounts)

    print(
        f"[DEBUG] Final totals - checking: {checking_total}, credit: {credit_total}")
    print(
        f"[DEBUG] Account counts - checking: {len(checking_accounts)}, credit: {len(credit_accounts)}")

    result = {
        "checking": {
            "accounts": checking_accounts,
            "total": checking_total,
            "count": len(checking_accounts)
        },
        "credit": {
            "accounts": credit_accounts,
            "total": credit_total,
            "count": len(credit_accounts)
        },
        # Credit balances are negative for debt
        "net_worth": checking_total + credit_total
    }

    print(f"[DEBUG] Final result: {result}")
    return result


def get_low_balance_accounts(conn: sqlite3.Connection, user_id: str, lookback_days: int = 30) -> List[Dict]:
    """
    Get accounts that are below their type-specific thresholds.
    """
    # Get recent balances
    rows = conn.execute(
        """
        SELECT DISTINCT account_id, date, balance FROM transactions
        WHERE user_id = ? AND balance IS NOT NULL AND date >= DATE('now', ?)
        ORDER BY account_id, date DESC
        """,
        (user_id, f"-{lookback_days} day"),
    ).fetchall()

    low_accounts = []
    seen_accounts = set()

    for r in rows:
        account_id = r["account_id"] or ""
        if account_id in seen_accounts:
            continue
        seen_accounts.add(account_id)

        balance = float(r["balance"])
        threshold = get_account_threshold(account_id)
        account_type = get_account_type(account_id)

        if balance < threshold:
            low_accounts.append({
                "account_id": account_id,
                "balance": balance,
                "threshold": threshold,
                "account_type": account_type,
                "date": r["date"]
            })

    return low_accounts
