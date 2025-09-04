from __future__ import annotations

from typing import Dict, Optional
import sqlite3

try:
    from ..ai_categorizer import (
        train_for_user as _train_categorizer,
        predict_for_user as _predict_categorizer,
    )
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False
    from ..ai_categorizer import train_global as _train_global


def train_categorizer(conn: sqlite3.Connection, user_id: str, min_per_class: Optional[int] = 5) -> Dict:
    if not AI_AVAILABLE:
        raise RuntimeError("AI categorizer unavailable")
    info = _train_categorizer(conn, user_id, min_per_class=min_per_class or 5)
    # Normalize Counter to dict if present
    counts = info.get("counts")
    if counts is not None and hasattr(counts, "items"):
        info["counts"] = {k: int(v) for k, v in counts.items()}
    return info


def predict_categorizer(user_id: str, merchant: Optional[str], description: Optional[str], top_k: int = 3) -> Dict:
    if not AI_AVAILABLE:
        raise RuntimeError("AI categorizer unavailable")
    return _predict_categorizer(user_id, merchant, description, top_k=top_k)


def train_global_categorizer(min_per_class: Optional[int] = 5) -> Dict:
    """Train a single global model from CSV files under data/training/."""
    # When sklearn is unavailable, train_global still works via fallback JSON
    from ..ai_categorizer import train_global as _train_global
    return _train_global(min_per_class=min_per_class or 5)
