from __future__ import annotations

from typing import Dict, List, Tuple
from datetime import date, timedelta, datetime
import json

import sqlite3

try:
    from sklearn.ensemble import IsolationForest
    SK_AVAILABLE = True
except Exception:
    SK_AVAILABLE = False


def _recent_expenses_for_merchant(conn: sqlite3.Connection, user_id: str, merchant: str, days: int = 180) -> List[Tuple[str, float]]:
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT date, amount FROM transactions
        WHERE user_id = ? AND amount < 0 AND LOWER(COALESCE(merchant,'')) = ? AND date >= ?
        ORDER BY date ASC
        """,
        (user_id, merchant.lower(), since),
    ).fetchall()
    return [(r["date"], float(r["amount"])) for r in rows]


def _features(series: List[Tuple[str, float]]) -> List[List[float]]:
    X = []
    for d, amt in series:
        try:
            dt = datetime.fromisoformat(d)
        except Exception:
            # fallback parse
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
            except Exception:
                continue
        X.append([
            abs(float(amt)),
            dt.day / 31.0,
            dt.weekday() / 6.0,
        ])
    return X


def detect_iforest_insights(conn: sqlite3.Connection, user_id: str, contamination: float = 0.08) -> List[Dict]:
    if not SK_AVAILABLE:
        return []

    # Pick merchants with at least 8 recent expenses
    since = (date.today() - timedelta(days=180)).isoformat()
    rows = conn.execute(
        """
        SELECT LOWER(COALESCE(merchant,'')) AS m, COUNT(*) as n
        FROM transactions
        WHERE user_id = ? AND amount < 0 AND date >= ?
        GROUP BY m HAVING n >= 8
        """,
        (user_id, since),
    ).fetchall()

    insights: List[Dict] = []
    for r in rows:
        m = r["m"]
        series = _recent_expenses_for_merchant(conn, user_id, m, 180)
        X = _features(series)
        if len(X) < 8:
            continue
        clf = IsolationForest(contamination=contamination, random_state=42)
        preds = clf.fit_predict(X)
        scores = clf.score_samples(X)
        # Flag the last transaction as outlier if predicted -1
        if preds[-1] == -1:
            last_date, last_amt = series[-1]
            insights.append({
                "id": f"iforest|{user_id}|{m}|{last_date}",
                "user_id": user_id,
                "type": "ml_outlier",
                "title": f"Possible outlier at {m}",
                "body": f"Latest charge ${abs(last_amt):.0f} appears anomalous vs your 6-month pattern (IsolationForest).",
                "severity": "warn",
                "data_json": json.dumps({
                    "merchant": m,
                    "last_date": last_date,
                    "last_amount": abs(last_amt),
                    "window_days": 180,
                    "model": "IsolationForest",
                    "contamination": contamination,
                    "score": float(scores[-1]),
                }),
            })
    return insights

