#!/usr/bin/env python3
"""
Bulk trainer: ingest per-user CSVs from training/*.csv, derive weak labels, and train models.

Usage:
  python services/api/scripts/train_from_folder.py training/
"""
import sys
from pathlib import Path
import sqlite3

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import db as db_mod  # type: ignore
from app.ingest import parse_csv_transactions  # type: ignore
from app.subscriptions import detect_subscriptions_for_user, upsert_subscriptions  # type: ignore
from app.ai_categorizer import train_for_user as train_cat  # type: ignore
from app.is_recurring_model import train_for_user as train_rec  # type: ignore


def main(folder: Path):
    db_mod.init_db()
    files = sorted(folder.glob('*.csv'))
    if not files:
        print(f"No CSVs found in {folder}")
        return 1
    for f in files:
        user_id = f.stem  # e.g., user1.csv -> user1
        print(f"== Training for user {user_id} from {f}")
        content = f.read_bytes()
        records = parse_csv_transactions(content, user_id=user_id, default_account_id=f"{user_id}_acct")
        with db_mod.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
            # Insert transactions (idempotent)
            for r in records:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO transactions (id, user_id, account_id, date, amount, merchant, description,
                        category, category_source, category_provenance, is_recurring, mcc, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["id"], r["user_id"], r.get("account_id"), r["date"], r["amount"], r.get("merchant"),
                        r.get("description"), r.get("category"), r.get("category_source"), r.get("category_provenance"),
                        r.get("is_recurring", False), r.get("mcc"), r.get("source", "csv"),
                    ),
                )
            # Weak labels via subscriptions detector (recurring)
            subs = detect_subscriptions_for_user(conn, user_id)
            upsert_subscriptions(conn, user_id, subs)
            # Train models
            try:
                cat_info = train_cat(conn, user_id, min_per_class=5)
                print(f"  categorizer: {cat_info}")
            except Exception as e:
                print(f"  categorizer: skipped ({e})")
            try:
                rec_info = train_rec(conn, user_id)
                print(f"  is_recurring: {rec_info}")
            except Exception as e:
                print(f"  is_recurring: skipped ({e})")
    print("Done.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: train_from_folder.py <training_folder>")
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))

