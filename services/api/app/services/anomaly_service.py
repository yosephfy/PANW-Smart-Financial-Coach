from __future__ import annotations

from typing import Dict, List
import sqlite3

from ..anomaly import detect_iforest_insights
from ..insights import upsert_insights


def iforest_detect(conn: sqlite3.Connection, user_id: str, contamination: float = 0.08) -> Dict:
    items: List[Dict] = detect_iforest_insights(conn, user_id, contamination=contamination) or []
    if items:
        upsert_insights(conn, items)
    return {"user_id": user_id, "count": len(items), "sample": items[0] if items else None}

