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


def _insight_id(user_id: str, kind: str, key: str) -> str:
    raw = f"{user_id}|{kind}|{key}|{_today().isoformat()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


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


def upsert_insights(conn: sqlite3.Connection, items: List[Dict]):
    for x in items:
        conn.execute(
            """
            INSERT OR REPLACE INTO insights (id, user_id, type, title, body, severity, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                x["id"], x["user_id"], x["type"], x["title"], x["body"], x["severity"], x.get(
                    "data_json"),
            ),
        )
