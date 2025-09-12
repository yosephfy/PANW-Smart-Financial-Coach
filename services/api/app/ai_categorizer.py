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


def global_model_path() -> Path:
    return _model_dir() / "global.joblib"


def has_model(user_id: str) -> bool:
    """Compatibility: report True if a per-user or global model exists."""
    return model_path(user_id).exists() or global_model_path().exists()


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
        # prepare serializable counts
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
        if not p.exists():
            p = global_model_path()
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
        p = global_model_path()
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


# -------- Global training from CSVs --------

def _iter_training_csv_paths() -> List[Path]:
    base = _repo_root() / "data"
    candidates: List[Path] = []
    # Prefer data/training/*.csv
    train_dir = base / "training"
    if train_dir.exists():
        for p in sorted(train_dir.glob("*.csv")):
            candidates.append(p)
    # Fallback: common sample training filenames
    samples = base / "samples"
    for name in [
        "transactions_training_2024-2025.csv",
        "transactions_training_2024_2025.csv",
        "transactions_sample.csv",
    ]:
        p = samples / name
        if p.exists():
            candidates.append(p)
    # De-duplicate while preserving order
    out: List[Path] = []
    seen = set()
    for p in candidates:
        s = str(p.resolve())
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def _read_csv_text_label(p: Path) -> Tuple[List[str], List[str]]:
    import csv
    texts: List[str] = []
    labels: List[str] = []
    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cat = (row.get("category") or "").strip()
            if not cat:
                continue
            merchant = (row.get("merchant") or row.get("name") or "").strip()
            desc = (row.get("description") or row.get("details")
                    or row.get("memo") or merchant).strip()
            text = f"{merchant} {desc}".strip()
            if not text:
                continue
            texts.append(text)
            labels.append(cat.lower())
    return texts, labels


def _split_indices(n: int) -> Tuple[List[int], List[int]]:
    """Return (train_idx, test_idx) using a deterministic 80/20 split."""
    import random
    rng = random.Random(42)
    idxs = list(range(n))
    rng.shuffle(idxs)
    n_train = int(0.8 * n)
    train = idxs[:n_train]
    test = idxs[n_train:]
    return train, test


def train_global(min_per_class: int = 5) -> Dict:
    """Train a single global model from CSV files under data/training/.

    Ignores user_id. Uses 80% train, 10% test, 10% val (deterministic shuffle).
    Saves to models/ai_categorizer/global.joblib (or JSON fallback).
    Returns metrics and class counts.
    """
    paths = _iter_training_csv_paths()
    if not paths:
        raise RuntimeError("no_training_csvs_found")
    all_texts: List[str] = []
    all_labels: List[str] = []
    for p in paths:
        t, y = _read_csv_text_label(p)
        all_texts.extend(t)
        all_labels.extend(y)
    if not all_texts:
        raise RuntimeError("no_labeled_rows_in_csvs")
    # filter classes with enough samples
    counts = Counter(all_labels)
    keep = {c for c, n in counts.items() if n >= min_per_class}
    data = [(t, y) for t, y in zip(all_texts, all_labels) if y in keep]
    if len(data) < 10 or len({y for _, y in data}) < 2:
        raise RuntimeError("not_enough_training_data")
    texts, labels = zip(*data)
    texts, labels = list(texts), list(labels)

    # Split (80/20)
    train_idx, test_idx = _split_indices(len(texts))

    def sel(idxs):
        return [texts[i] for i in idxs], [labels[i] for i in idxs]
    X_train, y_train = sel(train_idx)
    X_test, y_test = sel(test_idx)

    if not SKLEARN_AVAILABLE:
        # Token-count fallback
        token_map = {}
        cls_counts = Counter(y_train)
        for text, label in zip(X_train, y_train):
            for tok in text.lower().split():
                token_map.setdefault(label, {}).setdefault(tok, 0)
                token_map[label][tok] += 1
        model = {"classes": list(cls_counts.keys()), "counts": {k: int(
            v) for k, v in cls_counts.items()}, "tokens": token_map}
        _save_fallback_model(global_model_path(), model)
        acc = None
    else:
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(
                1, 2), min_df=1, max_features=30000)),
            ("clf", LogisticRegression(max_iter=200, class_weight="balanced")),
        ])
        pipe.fit(X_train, y_train)
        joblib.dump(pipe, global_model_path())
        # quick test accuracy
        try:
            acc = float(pipe.score(X_test, y_test)) if X_test else None
        except Exception:
            acc = None

    return {
        "model": "global",
        "n_samples": len(texts),
        "classes": sorted(list({c for c in labels})),
        "counts": {k: int(v) for k, v in Counter(labels).items()},
        "train_size": len(X_train),
        "test_size": len(X_test),
        "val_size": 0,
        "test_accuracy": acc,
        "paths": [str(p) for p in paths],
    }
