import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sqlite3

try:
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    import joblib
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False
    # lightweight JSON fallback helpers when sklearn isn't installable
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
    p = _repo_root() / "models" / "ai_categorizer"
    p.mkdir(parents=True, exist_ok=True)
    return p


def model_path(user_id: str) -> Path:
    return _model_dir() / f"{user_id}.joblib"


def has_model(user_id: str) -> bool:
    return model_path(user_id).exists()


def _gather_training_data(conn: sqlite3.Connection, user_id: str, min_per_class: int = 5) -> Tuple[List[str], List[str]]:
    rows = conn.execute(
        """
        SELECT COALESCE(merchant,'') as merchant, COALESCE(description,'') as description, COALESCE(category,'') as category
        FROM transactions
        WHERE user_id = ? AND category IS NOT NULL AND TRIM(category) != ''
        """,
        (user_id,),
    ).fetchall()
    texts: List[str] = []
    labels: List[str] = []
    for r in rows:
        text = f"{r['merchant']} {r['description']}".strip()
        if not text:
            continue
        labels.append(str(r['category']).lower())
        texts.append(text)
    # filter classes with enough samples
    counts = Counter(labels)
    keep = {c for c, n in counts.items() if n >= min_per_class}
    filtered = [(t, y) for t, y in zip(texts, labels) if y in keep]
    if not filtered:
        return [], []
    ft, fy = zip(*filtered)
    return list(ft), list(fy)


def train_for_user(conn: sqlite3.Connection, user_id: str, min_per_class: int = 5) -> Dict:
    if not SKLEARN_AVAILABLE:
        # fallback: simple token-frequency model stored as JSON
        X, y = _gather_training_data(
            conn, user_id, min_per_class=min_per_class)
        if len(X) < 10 or len(set(y)) < 2:
            raise RuntimeError("not_enough_training_data")
        from collections import defaultdict
        counts = defaultdict(int)
        token_map = {}
        for text, label in zip(X, y):
            counts[label] += 1
            for tok in text.lower().split():
                token_map.setdefault(label, {}).setdefault(tok, 0)
                token_map[label][tok] += 1
        # prepare serializable counts (convert defaultdict)
        serial_counts = {k: int(v) for k, v in counts.items()}
        model = {"classes": list(serial_counts.keys()),
                 "counts": serial_counts, "tokens": token_map}
        _save_fallback_model(model_path(user_id), model)
        return {"user_id": user_id, "classes": list(serial_counts.keys()), "counts": serial_counts, "n_samples": len(y)}
    X, y = _gather_training_data(conn, user_id, min_per_class=min_per_class)
    if len(X) < 10 or len(set(y)) < 2:
        raise RuntimeError("not_enough_training_data")
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000)),
        ("clf", LogisticRegression(max_iter=200, class_weight="balanced")),
    ])
    pipe.fit(X, y)
    joblib.dump(pipe, model_path(user_id))
    counts = Counter(y)
    return {"user_id": user_id, "classes": list(counts.keys()), "counts": counts, "n_samples": len(y)}


def predict_for_user(user_id: str, merchant: Optional[str], description: Optional[str], top_k: int = 3) -> Dict:
    if not SKLEARN_AVAILABLE:
        # fallback: score classes by token overlap / counts
        p = model_path(user_id)
        try:
            model = _load_fallback_model(p)
        except Exception:
            raise RuntimeError("model_not_found")
        text = f"{merchant or ''} {description or ''}".strip().lower()
        if not text:
            return {"predictions": []}
        toks = text.split()
        scores = {}
        for cls in model.get('classes', []):
            scores[cls] = 0.0
            tmap = model.get('tokens', {}).get(cls, {})
            for t in toks:
                scores[cls] += tmap.get(t, 0)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k]
        total = sum(v for _, v in ranked) or 1.0
        return {"predictions": [{"label": c, "prob": float(v) / float(total)} for c, v in ranked]}
    p = model_path(user_id)
    if not p.exists():
        raise RuntimeError("model_not_found")
    pipe: Pipeline = joblib.load(p)
    text = f"{merchant or ''} {description or ''}".strip()
    if not text:
        return {"predictions": []}
    proba = None
    if hasattr(pipe.named_steps["clf"], "predict_proba"):
        probs = pipe.predict_proba([text])[0]
        classes = list(pipe.named_steps["clf"].classes_)
        pairs = sorted(zip(classes, probs),
                       key=lambda x: x[1], reverse=True)[:top_k]
        return {"predictions": [{"label": c, "prob": float(p)} for c, p in pairs]}
    # fallback to decision_function
    scores = pipe.decision_function([text])
    if scores.ndim == 1:
        scores = [scores]
    classes = list(pipe.named_steps["clf"].classes_)
    pairs = sorted(zip(classes, scores[0]),
                   key=lambda x: x[1], reverse=True)[:top_k]
    # normalize scores to 0..1 via min-max (rough)
    svals = [s for _, s in pairs]
    if svals:
        smin, smax = min(svals), max(svals)
        def norm(s): return float((s - smin) / (smax - smin + 1e-9))
    else:
        def norm(s): return 0.0
    return {"predictions": [{"label": c, "prob": norm(s)} for c, s in pairs]}
