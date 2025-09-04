from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import sqlite3

from ..repositories import transactions_repo as txrepo
from ..ingest import dupe_hash


class AIHooks:
    def __init__(self,
                 has_model: Callable[[str], bool] | None = None,
                 predict: Callable[[str, Optional[str], Optional[str]], Dict[str, Any]] | None = None) -> None:
        self.has_model = has_model
        self.predict = predict


class RecHooks:
    def __init__(self,
                 has_model: Callable[[str], bool] | None = None,
                 predict: Callable[[str, Optional[str], Optional[str], float, str], Dict[str, Any]] | None = None) -> None:
        self.has_model = has_model
        self.predict = predict


def ingest_records(conn: sqlite3.Connection,
                   user_id: str,
                   records: List[Dict[str, Any]],
                   default_account_id: Optional[str] = None,
                   ai: Optional[AIHooks] = None,
                   rec: Optional[RecHooks] = None) -> Dict[str, Any]:
    """Insert parsed transaction records for a user with enrichment and dedupe.

    Returns { inserted, skipped, total_rows, sample }
    """
    if not records:
        return {"inserted": 0, "skipped": 0, "total_rows": 0}

    inserted = 0
    skipped = 0
    seen_hashes = set()

    # Ensure user exists
    txrepo.ensure_user(conn, user_id)

    # If no account ids are present and no default was provided, create a sensible default
    auto_account_id = None
    if not default_account_id:
        auto_account_id = f"{user_id}_default"
        for r in records:
            if not r.get("account_id"):
                r["account_id"] = auto_account_id

    # Ensure default/auto account exists
    if default_account_id:
        txrepo.ensure_account(conn, default_account_id, user_id, name="Default Account")
    elif auto_account_id:
        txrepo.ensure_account(conn, auto_account_id, user_id, name="Default Account")

    # Ensure any referenced accounts exist and apply optional enrichments
    for r in records:
        acc_id = r.get("account_id")
        if acc_id:
            txrepo.ensure_account(conn, acc_id, user_id, name=r.get("account_name") or "Imported")

        # AI categorization fallback
        if ai and ai.has_model and ai.predict and ai.has_model(user_id):
            if not r.get("category") or (r.get("category_source") in (None, "fallback", "regex")):
                try:
                    pred = ai.predict(user_id, r.get("merchant"), r.get("description"))
                    preds = pred.get("predictions", [])
                    if preds:
                        top = preds[0]
                        prob = float(top.get("prob", 0.0))
                        if prob >= 0.7:
                            r["category"] = top.get("label")
                            r["category_source"] = "ml"
                            r["category_provenance"] = f"ml:{r['category']}:{prob:.2f}"
                except Exception:
                    pass

        # Recurring prediction
        if rec and rec.has_model and rec.predict and rec.has_model(user_id):
            if not r.get("is_recurring"):
                try:
                    pr = rec.predict(user_id, r.get("merchant"), r.get("description"), float(r["amount"]), r["date"])
                    if float(pr.get("prob", 0.0)) >= 0.6:
                        r["is_recurring"] = True
                except Exception:
                    pass

    # Insert with dedupe (by date/amount/merchant per user)
    for r in records:
        h = dupe_hash(user_id, r["date"], r["amount"], r.get("merchant"))
        if h in seen_hashes:
            skipped += 1
            continue

        merchant_norm = (r.get("merchant") or "").strip().lower()
        amount_cents = int(round(float(r["amount"]) * 100))
        if txrepo.exists_duplicate(conn, user_id, r["date"], amount_cents, merchant_norm):
            skipped += 1
            continue

        ok = False
        try:
            ok = txrepo.insert_transaction(conn, r)
        except Exception:
            ok = False
        if ok:
            inserted += 1
            seen_hashes.add(h)
        else:
            skipped += 1

    sample = records[0] if records else None
    if sample and "raw" in sample:
        sample.pop("raw", None)
    return {"inserted": inserted, "skipped": skipped, "total_rows": len(records), "sample": sample}

