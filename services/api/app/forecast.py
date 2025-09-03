from __future__ import annotations

from typing import Dict, List, Tuple
import sqlite3
from datetime import date


def _monthly_category_spend(conn: sqlite3.Connection, user_id: str, months: int = 6) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date) AS ym,
               LOWER(COALESCE(category,'')) AS category,
               SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS spend
        FROM transactions
        WHERE user_id = ?
        GROUP BY ym, category
        ORDER BY ym DESC
        LIMIT ?
        """,
        (user_id, months * 50),  # rough cap
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    order: List[str] = []
    for r in rows:
        ym = r["ym"]
        cat = r["category"] or "uncategorized"
        spend = float(r["spend"] or 0.0)
        out.setdefault(cat, {})[ym] = spend
        if ym not in order:
            order.append(ym)
    return [{"category": c, **vals} for c, vals in out.items()]


def _weighted_forecast(series: List[float]) -> float:
    if not series:
        return 0.0
    if len(series) == 1:
        return series[0]
    if len(series) == 2:
        return 0.6 * series[-1] + 0.4 * series[-2]
    # 50% last month, 30% prev, 20% mean of earlier
    last, prev, rest = series[-1], series[-2], series[:-2]
    base = sum(rest)/len(rest) if rest else prev
    return 0.5 * last + 0.3 * prev + 0.2 * base


def forecast_categories(conn: sqlite3.Connection, user_id: str, months_history: int = 6, top_k: int = 8) -> Dict:
    data = _monthly_category_spend(conn, user_id, months_history)
    # assemble chronological months
    months = [r[0] for r in conn.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) AS ym FROM transactions WHERE user_id = ? ORDER BY ym ASC",
        (user_id,),
    ).fetchall()]
    if not months:
        return {"forecasts": []}
    last_month = months[-1]
    # build forecasts
    results = []
    for row in data:
        cat = row.pop("category")
        series = [row.get(m, 0.0) for m in months[-months_history:]]
        hist = [v for v in series if v > 0]
        if len(hist) < 2:
            continue
        pred = _weighted_forecast(hist)
        results.append({
            "category": cat,
            "forecast_next_month": round(pred, 2),
            "history_months": months[-len(series):],
            "history_values": series,
        })
    results.sort(key=lambda x: x["forecast_next_month"], reverse=True)
    return {"last_month": last_month, "forecasts": results[:top_k]}

