from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import hashlib

import sqlite3

try:
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    import joblib
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False
    # lightweight JSON fallback for recurring model
    import json

    def _save_fallback_model(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path.with_suffix('.json'), 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)

    def _load_fallback_model(path):
        p = path.with_suffix('.json')
        if not p.exists():
            raise FileNotFoundError(str(p))
        with open(p, 'r', encoding='utf-8') as fh:
            return json.load(fh)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _model_dir() -> Path:
    p = _repo_root() / "models" / "is_recurring"
    p.mkdir(parents=True, exist_ok=True)
    return p


def model_path(user_id: str) -> Path:
    return _model_dir() / f"{user_id}.joblib"


def has_model(user_id: str) -> bool:
    return model_path(user_id).exists()


def _label_from_subscriptions(conn: sqlite3.Connection, user_id: str) -> Dict[str, int]:
    # Return a set of merchants considered recurring from subscriptions table
    rows = conn.execute(
        "SELECT LOWER(merchant) AS m FROM subscriptions WHERE user_id = ? AND status = 'active'",
        (user_id,),
    ).fetchall()
    return {r["m"]: 1 for r in rows}


def _gather_training_data(conn: sqlite3.Connection, user_id: str, months: int = 18) -> Tuple[List[str], List[int]]:
    recur_merchants = _label_from_subscriptions(conn, user_id)
    # Pull last N months of expenses
    rows = conn.execute(
        """
        SELECT date, amount, COALESCE(merchant,'') AS merchant, COALESCE(description,'') AS description
        FROM transactions
        WHERE user_id = ? AND amount < 0
        ORDER BY date DESC
        LIMIT 20000
        """,
        (user_id,),
    ).fetchall()
    X: List[str] = []
    y: List[int] = []
    for r in rows:
        merch = (r["merchant"] or "").strip().lower()
        desc = (r["description"] or "").strip().lower()
        amt = abs(float(r["amount"]))
        d = r["date"]
        # features baked into text for simplicity
        try:
            dt = datetime.fromisoformat(d)
        except Exception:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
            except Exception:
                dt = datetime.utcnow()
        dom = dt.day
        wkd = dt.weekday()
        amt_bin = int(amt // 5)  # 5-unit bins
        text = f"{merch} {desc} AMT_{amt_bin} DOM_{dom} WKD_{wkd}"
        X.append(text)
        y.append(1 if merch in recur_merchants else 0)
    # Ensure both classes exist
    if sum(y) == 0 or sum(y) == len(y):
        return [], []
    return X, y


def train_for_user(conn: sqlite3.Connection, user_id: str) -> Dict:
    if not SKLEARN_AVAILABLE:
        # fallback: simple rule-based recurring model persisted as JSON
        X, y = _gather_training_data(conn, user_id)
        if len(X) < 20:
            raise RuntimeError("not_enough_training_data")
        # create merchant -> positive count map
        pos_counts = {}
        total_counts = {}
        for text, label in zip(X, y):
            # merchant is first token in text (as built in _gather_training_data)
            parts = text.split()
            merch = parts[0] if parts else ''
            total_counts[merch] = total_counts.get(merch, 0) + 1
            if label == 1:
                pos_counts[merch] = pos_counts.get(merch, 0) + 1
        model = {"pos_counts": pos_counts, "total_counts": total_counts}
        _save_fallback_model(model_path(user_id), model)
        return {"user_id": user_id, "n_samples": len(y), "pos": int(sum(y)), "neg": int(len(y) - sum(y))}
    X, y = _gather_training_data(conn, user_id)
    if len(X) < 20:
        raise RuntimeError("not_enough_training_data")
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=40000)),
        ("clf", LogisticRegression(max_iter=300, class_weight="balanced")),
    ])
    pipe.fit(X, y)
    import joblib
    joblib.dump(pipe, model_path(user_id))
    return {"user_id": user_id, "n_samples": len(y), "pos": int(sum(y)), "neg": int(len(y) - sum(y))}


def predict_for_user(user_id: str, merchant: Optional[str], description: Optional[str], amount: float, date_str: str) -> Dict:
    if not SKLEARN_AVAILABLE:
        p = model_path(user_id)
        try:
            model = _load_fallback_model(p)
        except Exception:
            raise RuntimeError("model_not_found")
        merch = (merchant or "").strip().lower()
        # heuristic: probability = pos_count / total_count for merchant (smoothed)
        pos = model.get('pos_counts', {}).get(merch, 0)
        tot = model.get('total_counts', {}).get(merch, 0)
        prob = (pos + 1) / (tot + 2) if tot >= 0 else 0.0
        return {"prob": float(prob), "label": int(prob >= 0.6)}
    p = model_path(user_id)
    if not p.exists():
        raise RuntimeError("model_not_found")
    import joblib
    pipe: Pipeline = joblib.load(p)
    merch = (merchant or "").strip().lower()
    desc = (description or "").strip().lower()
    amt = abs(float(amount))
    try:
        dt = datetime.fromisoformat(date_str)
    except Exception:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            dt = datetime.utcnow()
    dom = dt.day
    wkd = dt.weekday()
    amt_bin = int(amt // 5)
    text = f"{merch} {desc} AMT_{amt_bin} DOM_{dom} WKD_{wkd}"
    prob = 0.0
    if hasattr(pipe.named_steps["clf"], "predict_proba"):
        prob = float(pipe.predict_proba([text])[0][1])
    else:
        score = float(pipe.decision_function([text])[0])
        prob = 1.0 / (1.0 + pow(2.71828, -score))
    return {"prob": prob, "label": int(prob >= 0.6)}
