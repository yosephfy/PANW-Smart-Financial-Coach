from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
import json


DISCRETIONARY_CATEGORIES = {
    "coffee", "food_delivery", "fast_food", "restaurants", "shopping", "rideshare", "subscriptions"
}


def _today() -> date:
    return date.today()


def _daterange(days: int) -> Tuple[str, str]:
    end = _today()
    start = end - timedelta(days=days-1)
    return start.isoformat(), end.isoformat()


def _spend_count_by(conn: sqlite3.Connection, user_id: str, start: str, end: str, field: str) -> Dict[str, Tuple[float, int]]:
    q = f"""
        SELECT LOWER(COALESCE({field}, '')) as key,
               SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as spend,
               SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as n_exp
        FROM transactions
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY key
    """
    rows = conn.execute(q, (user_id, start, end)).fetchall()
    out: Dict[str, Tuple[float, int]] = {}
    for r in rows:
        k = r["key"] or ""
        out[k] = (float(r["spend"] or 0.0), int(r["n_exp"] or 0))
    return out


def _recent_tx_for_merchant(conn: sqlite3.Connection, user_id: str, merchant: str, days: int = 90) -> List[Tuple[str, float]]:
    start = (_today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT date, amount FROM transactions
        WHERE user_id = ? AND LOWER(COALESCE(merchant,'')) = ? AND date >= ?
        ORDER BY date ASC
        """,
        (user_id, merchant.lower(), start),
    ).fetchall()
    # Only expenses
    return [(r["date"], float(r["amount"])) for r in rows if float(r["amount"]) < 0]


def _mean_std(vals: List[float]) -> Tuple[float, float]:
    if not vals:
        return (0.0, 0.0)
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return (mean, 0.0)
    var = sum((x - mean) ** 2 for x in vals) / (n - 1)
    std = var ** 0.5
    return (mean, std)


def _insight_id(user_id: str, kind: str, key: str, suffix: str = "") -> str:
    raw = f"{user_id}|{kind}|{key}|{_today().isoformat()}{suffix}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _transaction_insight_id(user_id: str, kind: str, key: str, transaction_id: str) -> str:
    """Generate insight ID for transaction-specific insights"""
    raw = f"{user_id}|{kind}|{key}|tx:{transaction_id}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def generate_transaction_insights(conn: sqlite3.Connection, user_id: str, transaction: Dict) -> List[Dict]:
    """Generate insights specifically for a newly added transaction."""
    insights: List[Dict] = []

    # Extract transaction info
    tx_id = transaction["id"]
    tx_amount = float(transaction["amount"])
    tx_date = transaction["date"]
    tx_merchant = transaction.get("merchant", "").lower(
    ) if transaction.get("merchant") else ""
    tx_category = transaction.get("category", "").lower(
    ) if transaction.get("category") else ""

    # Only generate insights for expenses
    if tx_amount >= 0:
        return insights

    expense_amount = abs(tx_amount)

    # 1. Sudden Expense Spike Detection
    # Check if this transaction is unusually large compared to recent transactions in the same category
    if tx_category and expense_amount >= 20:
        # Get recent transactions in same category (last 30 days, excluding today)
        yesterday = (date.fromisoformat(tx_date) -
                     timedelta(days=1)).isoformat()
        thirty_days_ago = (date.fromisoformat(tx_date) -
                           timedelta(days=30)).isoformat()

        recent_amounts = conn.execute(
            """
            SELECT amount FROM transactions
            WHERE user_id = ? AND LOWER(COALESCE(category,'')) = ? 
            AND date BETWEEN ? AND ? AND amount < 0
            """,
            (user_id, tx_category, thirty_days_ago, yesterday),
        ).fetchall()

        if len(recent_amounts) >= 3:  # Need some history for comparison
            amounts = [abs(float(r["amount"])) for r in recent_amounts]
            mean_amount = sum(amounts) / len(amounts)

            # If current transaction is 2x the average or >$50 more than average
            if expense_amount >= max(mean_amount * 2.0, mean_amount + 50.0):
                insights.append({
                    "id": _transaction_insight_id(user_id, "expense_spike", tx_category, tx_id),
                    "user_id": user_id,
                    "type": "expense_spike",
                    "title": f"Unusually high {tx_category} expense",
                    "body": f"${expense_amount:.0f} at {tx_merchant or 'merchant'} is {expense_amount/mean_amount:.1f}x your avg ${mean_amount:.0f} in this category.",
                    "severity": "warn" if expense_amount < mean_amount * 3 else "critical",
                    "data_json": json.dumps({
                        "transaction_id": tx_id,
                        "category": tx_category,
                        "amount": expense_amount,
                        "average_amount": mean_amount,
                        "spike_ratio": expense_amount / mean_amount,
                        "merchant": tx_merchant,
                    }),
                })

    # 2. Merchant Spending Spike Detection
    if tx_merchant and expense_amount >= 20:
        # Check spending at this merchant in last 90 days
        ninety_days_ago = (date.fromisoformat(tx_date) -
                           timedelta(days=90)).isoformat()
        yesterday = (date.fromisoformat(tx_date) -
                     timedelta(days=1)).isoformat()

        merchant_history = conn.execute(
            """
            SELECT amount FROM transactions
            WHERE user_id = ? AND LOWER(COALESCE(merchant,'')) = ? 
            AND date BETWEEN ? AND ? AND amount < 0
            """,
            (user_id, tx_merchant, ninety_days_ago, yesterday),
        ).fetchall()

        if len(merchant_history) >= 2:  # Need some history
            amounts = [abs(float(r["amount"])) for r in merchant_history]
            mean_amount = sum(amounts) / len(amounts)
            max_amount = max(amounts)

            # If this is significantly higher than usual at this merchant
            if expense_amount >= max(mean_amount * 2.5, max_amount * 1.2):
                insights.append({
                    "id": _transaction_insight_id(user_id, "merchant_spike", tx_merchant.replace(" ", "_"), tx_id),
                    "user_id": user_id,
                    "type": "merchant_spike",
                    "title": f"Higher than usual at {tx_merchant.title()}",
                    "body": f"${expense_amount:.0f} vs typical ${mean_amount:.0f} (previous max: ${max_amount:.0f}).",
                    "severity": "info",
                    "data_json": json.dumps({
                        "transaction_id": tx_id,
                        "merchant": tx_merchant,
                        "amount": expense_amount,
                        "average_amount": mean_amount,
                        "previous_max": max_amount,
                    }),
                })

    # 3. Daily Spending Alert
    # Check if today's total spending is high
    today_total = conn.execute(
        """
        SELECT SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as total
        FROM transactions
        WHERE user_id = ? AND date = ? AND amount < 0
        """,
        (user_id, tx_date),
    ).fetchone()

    if today_total and today_total["total"]:
        total_today = float(today_total["total"])

        # Get average daily spending over last 30 days
        thirty_days_ago = (date.fromisoformat(tx_date) -
                           timedelta(days=30)).isoformat()
        yesterday = (date.fromisoformat(tx_date) -
                     timedelta(days=1)).isoformat()

        daily_totals = conn.execute(
            """
            SELECT date, SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as daily_total
            FROM transactions
            WHERE user_id = ? AND date BETWEEN ? AND ? AND amount < 0
            GROUP BY date
            HAVING daily_total > 0
            """,
            (user_id, thirty_days_ago, yesterday),
        ).fetchall()

        if len(daily_totals) >= 10:  # Need reasonable history
            avg_daily = sum(float(r["daily_total"])
                            for r in daily_totals) / len(daily_totals)

            # If today is 2x average daily spend and >$100
            if total_today >= max(avg_daily * 2.0, 100.0) and total_today >= avg_daily + 50:
                insights.append({
                    "id": _transaction_insight_id(user_id, "daily_spend_high", tx_date, tx_id),
                    "user_id": user_id,
                    "type": "daily_spend_high",
                    "title": "High spending day",
                    "body": f"${total_today:.0f} spent today vs your avg ${avg_daily:.0f}/day. This transaction brought you over the threshold.",
                    "severity": "info",
                    "data_json": json.dumps({
                        "transaction_id": tx_id,
                        "date": tx_date,
                        "total_today": total_today,
                        "average_daily": avg_daily,
                    }),
                })

    # 4. Enhanced Budget Category Warning
    if tx_category and expense_amount >= 15:
        # First check if there's a budget for this category
        budget_row = conn.execute(
            "SELECT monthly_budget FROM category_budgets WHERE user_id = ? AND LOWER(category) = ?",
            (user_id, tx_category)
        ).fetchone()

        # Check month-to-date spending in this category
        month_start = date.fromisoformat(tx_date).replace(day=1).isoformat()
        month_total = conn.execute(
            """
            SELECT SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as total
            FROM transactions
            WHERE user_id = ? AND LOWER(COALESCE(category,'')) = ? 
            AND date BETWEEN ? AND ? AND amount < 0
            """,
            (user_id, tx_category, month_start, tx_date),
        ).fetchone()

        if month_total and month_total["total"]:
            mtd_total = float(month_total["total"])

            if budget_row and budget_row["monthly_budget"]:
                # User has a budget set for this category
                budget = float(budget_row["monthly_budget"])
                usage_pct = (mtd_total / budget) * 100 if budget > 0 else 0

                if usage_pct >= 90:
                    # Budget-based alert
                    status = "over" if usage_pct >= 100 else "near"
                    insights.append({
                        "id": _transaction_insight_id(user_id, "budget_alert", tx_category, tx_id),
                        "user_id": user_id,
                        "type": "budget_alert",
                        "title": f"{tx_category} budget {status} limit",
                        "body": f"This ${expense_amount:.0f} transaction brings you to ${mtd_total:.0f} of ${budget:.0f} budget ({usage_pct:.0f}%).",
                        "severity": "critical" if usage_pct >= 100 else "warn",
                        "data_json": json.dumps({
                            "transaction_id": tx_id,
                            "category": tx_category,
                            "amount": expense_amount,
                            "mtd_total": mtd_total,
                            "budget": budget,
                            "usage_percentage": round(usage_pct, 1),
                        }),
                    })
                elif usage_pct >= 75:
                    # Budget progress alert
                    insights.append({
                        "id": _transaction_insight_id(user_id, "budget_progress", tx_category, tx_id),
                        "user_id": user_id,
                        "type": "budget_progress",
                        "title": f"{tx_category} budget progress",
                        "body": f"${mtd_total:.0f} of ${budget:.0f} used ({usage_pct:.0f}%). ${budget - mtd_total:.0f} remaining this month.",
                        "severity": "info",
                        "data_json": json.dumps({
                            "transaction_id": tx_id,
                            "category": tx_category,
                            "amount": expense_amount,
                            "mtd_total": mtd_total,
                            "budget": budget,
                            "remaining": budget - mtd_total,
                            "usage_percentage": round(usage_pct, 1),
                        }),
                    })
            elif tx_category in DISCRETIONARY_CATEGORIES:
                # No budget set, but compare to previous month for discretionary categories
                prev_month_start = (date.fromisoformat(tx_date).replace(
                    day=1) - timedelta(days=1)).replace(day=1).isoformat()
                prev_month_end = (date.fromisoformat(tx_date).replace(
                    day=1) - timedelta(days=1)).isoformat()

                prev_month_total = conn.execute(
                    """
                    SELECT SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as total
                    FROM transactions
                    WHERE user_id = ? AND LOWER(COALESCE(category,'')) = ? 
                    AND date BETWEEN ? AND ? AND amount < 0
                    """,
                    (user_id, tx_category, prev_month_start, prev_month_end),
                ).fetchone()

                prev_total = float(
                    prev_month_total["total"]) if prev_month_total and prev_month_total["total"] else 0

                # If we're already spending 80% of last month's total
                if prev_total > 0 and mtd_total >= prev_total * 0.8:
                    insights.append({
                        "id": _transaction_insight_id(user_id, "category_budget_alert", tx_category, tx_id),
                        "user_id": user_id,
                        "type": "category_budget_alert",
                        "title": f"High {tx_category} spending this month",
                        "body": f"${mtd_total:.0f} spent on {tx_category} this month (${prev_total:.0f} last month). Consider setting a budget or slowing down.",
                        "severity": "warn",
                        "data_json": json.dumps({
                            "transaction_id": tx_id,
                            "category": tx_category,
                            "month_to_date": mtd_total,
                            "previous_month": prev_total,
                            "percentage_of_prev": (mtd_total / prev_total) * 100 if prev_total > 0 else 0,
                            "suggest_budget": True,
                        }),
                    })

    return insights


def generate_insights(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    insights: List[Dict] = []

    # Windows
    cur_30_start, cur_30_end = _daterange(30)
    prev_30_start = (date.fromisoformat(cur_30_start) -
                     timedelta(days=30)).isoformat()
    prev_30_end = (date.fromisoformat(cur_30_start) -
                   timedelta(days=1)).isoformat()

    # Category overspend: current 30d vs previous 30d (only if prior window has enough data)
    cur_cat = _spend_count_by(
        conn, user_id, cur_30_start, cur_30_end, 'category')
    prev_cat = _spend_count_by(
        conn, user_id, prev_30_start, prev_30_end, 'category')

    for cat, (cur_val, cur_n) in cur_cat.items():
        prev_val, prev_n = prev_cat.get(cat, (0.0, 0))
        # Require sufficient prior signal to avoid false "increase" when no prior data
        if prev_n < 3 or prev_val < 50.0:
            continue
        if cur_val >= max(prev_val * 1.2, prev_val + 20.0) and cur_val >= 50.0:
            delta = cur_val - prev_val
            title = f"Overspend in {cat or 'uncategorized'}"
            body = f"You spent {cur_val:.0f} this 30d vs {prev_val:.0f} prior (+{delta:.0f}). Consider small cutbacks to hit goals."
            insights.append({
                "id": _insight_id(user_id, "overspend_category", cat or "uncategorized"),
                "user_id": user_id,
                "type": "overspend_category",
                "title": title,
                "body": body,
                "severity": "warn",
                "data_json": json.dumps({
                    "category": cat or "uncategorized",
                    "current_30d": cur_val,
                    "current_count": cur_n,
                    "previous_30d": prev_val,
                    "previous_count": prev_n,
                }),
            })

    # Trending categories: rank by growth rate
    growth: List[Tuple[str, float, float, float]] = []
    for cat in set(cur_cat.keys()) | set(prev_cat.keys()):
        c, c_n = cur_cat.get(cat, (0.0, 0))
        p, p_n = prev_cat.get(cat, (0.0, 0))
        # Require prior signal
        if p_n < 3 or p < 50.0:
            continue
        if c < 50.0:
            continue
        rate = (c - p) / max(p, 1.0)
        growth.append((cat, c, p, rate, c_n, p_n))
    growth.sort(key=lambda x: x[3], reverse=True)
    for cat, c, p, rate, c_n, p_n in growth[:5]:
        if rate <= 0.15:
            continue
        title = f"{cat or 'uncategorized'} trending up"
        body = f"Spend up {int(rate*100)}% vs prior 30d ({c:.0f} vs {p:.0f})."
        insights.append({
            "id": _insight_id(user_id, "trending_category", cat or "uncategorized"),
            "user_id": user_id,
            "type": "trending_category",
            "title": title,
            "body": body,
            "severity": "info",
            "data_json": json.dumps({
                "category": cat or "uncategorized",
                "current_30d": c,
                "current_count": c_n,
                "previous_30d": p,
                "previous_count": p_n,
                "growth_rate": rate,
            }),
        })

    # Merchant anomaly: last transaction vs 90d mean/std
    # Choose merchants with at least 3 transactions in last 90d
    merchants = conn.execute(
        """
        SELECT LOWER(COALESCE(merchant,'')) AS m, COUNT(*) as n
        FROM transactions
        WHERE user_id = ? AND amount < 0 AND date >= ?
        GROUP BY m HAVING n >= 3
        """,
        (user_id, (date.today() - timedelta(days=90)).isoformat()),
    ).fetchall()
    for row in merchants:
        m = row["m"]
        series = _recent_tx_for_merchant(conn, user_id, m, 90)
        if len(series) < 3:
            continue
        amounts = [abs(a) for _, a in series]
        mean, std = _mean_std(amounts)
        last_amount = amounts[-1]
        if std > 0 and (last_amount - mean) / std >= 2.5 and last_amount >= 20:
            title = f"Unusual charge at {m}"
            body = f"Latest charge {last_amount:.0f} vs avg {mean:.0f} (>{2.5:.1f}σ)."
            insights.append({
                "id": _insight_id(user_id, "merchant_anomaly", m),
                "user_id": user_id,
                "type": "merchant_anomaly",
                "title": title,
                "body": body,
                "severity": "warn",
                "data_json": json.dumps({
                    "merchant": m,
                    "last_amount": last_amount,
                    "mean": mean,
                    "std": std,
                }),
            })

    # Save suggestion: top discretionary categories, 20% cut potential
    disc_spend = []
    for cat, (amt, cnt) in cur_cat.items():
        if (cat in DISCRETIONARY_CATEGORIES) and amt >= 20:
            disc_spend.append((cat, amt))
    disc_spend.sort(key=lambda x: x[1], reverse=True)
    for cat, amt in disc_spend[:3]:
        save = round(amt * 0.2, 2)
        title = f"Save on {cat}"
        body = f"Cutting ~20% could save ~${save:.0f}/month."
        insights.append({
            "id": _insight_id(user_id, "save_suggestion", cat),
            "user_id": user_id,
            "type": "save_suggestion",
            "title": title,
            "body": body,
            "severity": "info",
            "data_json": json.dumps({
                "category": cat,
                "current_30d": amt,
                "suggested_cut_pct": 0.2,
                "suggested_savings": save,
            }),
        })

    return insights


# --- Additional generators: duplicate charges and budgets ---

def _month_start_end(today: date) -> Tuple[str, str]:
    start = today.replace(day=1)
    if start.month == 12:
        next_month = date(start.year + 1, 1, 1)
    else:
        next_month = date(start.year, start.month + 1, 1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def generate_duplicate_charge_insights(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    """Detect likely duplicate charges (same merchant and amount on the same day)."""
    rows = conn.execute(
        """
        SELECT date, COALESCE(merchant,'') as merchant,
               CAST(ROUND(amount * 100) AS INTEGER) AS amount_cents,
               COUNT(*) as cnt
        FROM transactions
        WHERE user_id = ? AND amount < 0
        GROUP BY date, merchant, amount_cents
        HAVING cnt >= 2
        ORDER BY date DESC
        """,
        (user_id,)
    ).fetchall()
    out: List[Dict] = []
    for r in rows:
        amt = abs(float(r["amount_cents"]) / 100.0)
        merchant = (r["merchant"] or "").lower() or "unknown"
        title = f"Possible duplicate charges at {merchant}"
        body = f"{r['cnt']} identical charges of ${amt:.2f} on {r['date']}. If unintentional, dispute or contact the merchant."
        out.append({
            "id": _insight_id(user_id, "dup_charge", f"{r['date']}|{merchant}|{amt:.2f}"),
            "user_id": user_id,
            "type": "dup_charge",
            "title": title,
            "body": body,
            "severity": "warn",
            "data_json": json.dumps({
                "date": r["date"],
                "merchant": merchant,
                "amount": amt,
                "count": int(r["cnt"]),
            })
        })
    return out


def generate_budget_overage_insights(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    """Compare MTD spend vs user-defined category budgets and emit overage insights."""
    # Load budgets
    budgets = conn.execute(
        "SELECT category, monthly_budget FROM category_budgets WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    if not budgets:
        return []
    today = _today()
    start, end = _month_start_end(today)
    out: List[Dict] = []

    for b in budgets:
        cat = (b["category"] or "").lower()
        mbud = float(b["monthly_budget"]
                     ) if b["monthly_budget"] is not None else 0.0
        if mbud <= 0:
            continue
        row = conn.execute(
            """
            SELECT SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS spend
            FROM transactions
            WHERE user_id = ? AND LOWER(COALESCE(category,'')) = ? AND date BETWEEN ? AND ?
            """,
            (user_id, cat, start, end),
        ).fetchone()
        mtd = float(row["spend"] or 0.0)

        # Enhanced budget insights with more granular feedback
        usage_pct = (mtd / mbud) * 100 if mbud > 0 else 0
        days_in_month = (date.fromisoformat(end) -
                         date.fromisoformat(start)).days + 1
        current_day = today.day
        expected_usage = (current_day / days_in_month) * 100

        if usage_pct >= 100:  # Over budget
            status = "over_budget"
            title = f"{cat} budget exceeded"
            body = f"${mtd:.0f} spent vs ${mbud:.0f} budget ({usage_pct:.0f}%). Consider adjusting spending this month."
            severity = "critical"
        elif usage_pct >= 90:  # Near budget limit
            status = "near_budget"
            title = f"{cat} budget nearly exhausted"
            body = f"${mtd:.0f} of ${mbud:.0f} budget used ({usage_pct:.0f}%). Only ${mbud - mtd:.0f} remaining."
            severity = "warn"
        elif usage_pct > expected_usage + 20:  # Spending too fast
            status = "ahead_of_pace"
            title = f"{cat} spending ahead of pace"
            body = f"{usage_pct:.0f}% of budget used but only {expected_usage:.0f}% through the month. Consider slowing down."
            severity = "warn"
        elif usage_pct < expected_usage - 15 and current_day > 10:  # Under-spending significantly
            status = "under_budget"
            title = f"{cat} budget on track"
            body = f"Great job! Only {usage_pct:.0f}% of budget used ({expected_usage:.0f}% expected). You have ${mbud - mtd:.0f} remaining."
            severity = "info"
        else:
            continue  # No insight needed for normal spending

        out.append({
            "id": _insight_id(user_id, "budget", cat + "_" + start + "_" + status),
            "user_id": user_id,
            "type": "budget",
            "title": title,
            "body": body,
            "severity": severity,
            "data_json": json.dumps({
                "category": cat,
                "mtd_spend": mtd,
                "budget": mbud,
                "usage_percentage": round(usage_pct, 1),
                "expected_usage_percentage": round(expected_usage, 1),
                "remaining": mbud - mtd,
                "status": status,
                "month_start": start,
            }),
        })
    return out


def generate_budget_suggestion_insights(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    """Suggest budgets for categories where user spends regularly but has no budget set."""
    # Get existing budgets
    existing_budgets = set()
    budget_rows = conn.execute(
        "SELECT LOWER(category) as category FROM category_budgets WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    for row in budget_rows:
        existing_budgets.add(row["category"])

    # Get spending by category in last 90 days
    three_months_ago = (date.today() - timedelta(days=90)).isoformat()
    today = date.today().isoformat()

    category_spending = conn.execute(
        """
        SELECT LOWER(COALESCE(category,'')) as category,
               SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as total_spend,
               COUNT(CASE WHEN amount < 0 THEN 1 END) as transaction_count,
               AVG(CASE WHEN amount < 0 THEN -amount END) as avg_amount
        FROM transactions
        WHERE user_id = ? AND date BETWEEN ? AND ? AND amount < 0
        GROUP BY LOWER(COALESCE(category,''))
        HAVING total_spend >= 100 AND transaction_count >= 3
        ORDER BY total_spend DESC
        """,
        (user_id, three_months_ago, today),
    ).fetchall()

    insights = []
    for row in category_spending[:5]:  # Top 5 spending categories
        category = row["category"] or "uncategorized"
        if category in existing_budgets or category == "":
            continue

        total_spend = float(row["total_spend"])
        transaction_count = int(row["transaction_count"])
        avg_amount = float(row["avg_amount"])

        # Suggest a monthly budget based on 90-day average + 10% buffer
        monthly_suggestion = round(
            (total_spend / 3) * 1.1, -1)  # Round to nearest $10

        insights.append({
            "id": _insight_id(user_id, "budget_suggestion", category),
            "user_id": user_id,
            "type": "budget_suggestion",
            "title": f"Consider setting a {category} budget",
            "body": f"You've spent ${total_spend:.0f} on {category} in 90 days ({transaction_count} transactions). Consider setting a ${monthly_suggestion:.0f}/month budget.",
            "severity": "info",
            "data_json": json.dumps({
                "category": category,
                "last_90_days_spend": total_spend,
                "transaction_count": transaction_count,
                "average_transaction": avg_amount,
                "suggested_monthly_budget": monthly_suggestion,
            }),
        })

    return insights


def generate_low_balance_insights(conn: sqlite3.Connection, user_id: str, lookback_days: int = 30) -> List[Dict]:
    """Generate insights for accounts with low balances using account type-specific thresholds."""
    from .utils.account_utils import get_low_balance_accounts

    insights: List[Dict] = []
    low_accounts = get_low_balance_accounts(conn, user_id, lookback_days)

    for acc in low_accounts:
        account_id = acc["account_id"]
        balance = acc["balance"]
        threshold = acc["threshold"]
        account_type = acc["account_type"]
        date_str = acc["date"]

        if account_type == "credit":
            # Credit card over limit
            title = f"Credit card approaching limit"
            body = f"Your {account_type} account {account_id} balance is ${balance:.2f}, approaching the recommended limit of ${threshold:.2f}."
        else:
            # Checking account low balance
            title = f"Low balance alert"
            body = f"Your {account_type} account {account_id} balance is ${balance:.2f}, below the safety threshold of ${threshold:.2f}."

        insights.append({
            "id": _insight_id(user_id, f"low_balance_{account_type}", account_id),
            "user_id": user_id,
            "type": f"low_balance_{account_type}",
            "title": title,
            "body": body,
            "severity": "warn",
            "data_json": json.dumps({
                "account_id": account_id,
                "account_type": account_type,
                "balance": balance,
                "threshold": threshold,
                "date": date_str
            }),
        })

    return insights
    """Emit insights when any recorded balance drops below a threshold in the lookback window."""
    rows = conn.execute(
        """
        SELECT date, account_id, balance FROM transactions
        WHERE user_id = ? AND balance IS NOT NULL AND date >= DATE('now', ?)
          AND balance < ?
        ORDER BY date DESC
        """,
        (user_id, f"-{lookback_days} day", threshold),
    ).fetchall()
    out: List[Dict] = []
    for r in rows:
        bal = float(r["balance"] or 0.0)
        acc = r["account_id"] or ""
        title = "Low balance warning"
        body = f"Balance ${bal:.0f} fell below ${threshold:.0f} on {r['date']} (acct {acc or '—'})."
        out.append({
            "id": _insight_id(user_id, "low_balance", f"{r['date']}|{acc}|{bal:.2f}"),
            "user_id": user_id,
            "type": "low_balance",
            "title": title,
            "body": body,
            "severity": "critical",
            "data_json": json.dumps({
                "date": r["date"],
                "account_id": acc,
                "balance": bal,
                "threshold": threshold,
            }),
        })
    return out


def upsert_insights(conn: sqlite3.Connection, items: List[Dict]):
    for x in items:
        conn.execute(
            """
            INSERT OR REPLACE INTO insights (
                id, user_id, type, title, body, severity, data_json,
                rewritten_title, rewritten_body, rewritten_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                x["id"], x["user_id"], x["type"], x["title"], x["body"], x["severity"],
                x.get("data_json"),
                x.get("rewritten_title"),
                x.get("rewritten_body"),
                x.get("rewritten_at"),
            ),
        )
