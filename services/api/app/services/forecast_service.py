from __future__ import annotations

from typing import Dict
import sqlite3

from ..forecast import forecast_categories as _forecast_categories


def categories_forecast(conn: sqlite3.Connection, user_id: str, months_history: int = 6, top_k: int = 8) -> Dict:
    return _forecast_categories(conn, user_id, months_history=months_history, top_k=top_k)

