from __future__ import annotations

from typing import Dict, List, Tuple
import sqlite3
from datetime import date

try:
    from sklearn.linear_model import Ridge
    SK_AVAILABLE = True
except Exception:
    SK_AVAILABLE = False


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
        # Try a small ML model if available and enough points, else fallback
        pred = None
        method = "weighted"
        if SK_AVAILABLE and len(hist) >= 3:
            try:
                # Train Ridge on t -> spend
                X = [[i] for i in range(len(hist))]
                y = hist
                model = Ridge(alpha=1.0)
                model.fit(X, y)
                pred = float(model.predict([[len(hist)]])[0])
                method = "ridge"
            except Exception:
                pred = None
        if pred is None:
            pred = _weighted_forecast(hist)
            method = "weighted"
        results.append({
            "category": cat,
            "forecast_next_month": round(pred, 2),
            "history_months": months[-len(series):],
            "history_values": series,
            "model": method,
        })
    results.sort(key=lambda x: x["forecast_next_month"], reverse=True)
    return {"last_month": last_month, "forecasts": results[:top_k]}


def forecast_net(conn: sqlite3.Connection, user_id: str, months_history: int = 6) -> Dict:
    # Net = income - expenses per month (sum(amount))
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date) AS ym, SUM(amount) AS net
        FROM transactions
        WHERE user_id = ?
        GROUP BY ym
        ORDER BY ym ASC
        """,
        (user_id,),
    ).fetchall()
    months = [r["ym"] for r in rows]
    vals = [float(r["net"] or 0.0) for r in rows]
    if not months:
        return {"forecast_next_month": 0.0, "history_months": [], "history_values": [], "model": "none"}
    hist = vals[-months_history:]
    # ML Ridge if possible, else weighted
    pred = None
    method = "weighted"
    if SK_AVAILABLE and len(hist) >= 3:
        try:
            X = [[i] for i in range(len(hist))]
            y = hist
            model = Ridge(alpha=1.0)
            model.fit(X, y)
            pred = float(model.predict([[len(hist)]])[0])
            method = "ridge"
        except Exception:
            pred = None
    if pred is None:
        pred = _weighted_forecast(hist)
        method = "weighted"
    return {
        "forecast_next_month": round(pred, 2),
        "history_months": months[-len(hist):],
        "history_values": hist,
        "model": method,
    }
