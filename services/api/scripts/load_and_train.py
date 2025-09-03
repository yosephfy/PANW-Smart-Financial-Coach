#!/usr/bin/env python3
"""Load sample CSV into dev DB and train ai categorizer for u_demo"""
from ai_categorizer import train_for_user, model_path, has_model
from db import get_connection, init_db
from ingest import parse_csv_transactions, dupe_hash
import sys
from pathlib import Path
# Compute path to services/api/app so we can import modules directly
repo = Path(__file__).resolve().parents[3]
app_dir = Path(__file__).resolve().parent.parent / 'app'
print('DEBUG repo root:', repo)
print('DEBUG app_dir:', app_dir)
sys.path.insert(0, str(app_dir))


CSV_PATH = repo / 'data' / 'samples' / 'transactions_sample.csv'
CSV_PATH = CSV_PATH.resolve()
USER_ID = 'u_demo'

if __name__ == '__main__':
    print('Initializing DB...')
    init_db()
    print('Reading CSV:', CSV_PATH)
    content = CSV_PATH.read_bytes()
    records = parse_csv_transactions(content, user_id=USER_ID)
    print('Parsed', len(records), 'records')
    inserted = 0
    skipped = 0
    with get_connection() as conn:
        conn.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (USER_ID,))
        # Ensure any referenced accounts exist
        for r in records:
            acc_id = r.get('account_id')
            if acc_id:
                conn.execute(
                    "INSERT OR IGNORE INTO accounts (id, user_id, name, type, institution, mask) VALUES (?, ?, ?, ?, ?, ?)",
                    (acc_id, USER_ID, r.get('account_name')
                     or 'Imported', None, None, None),
                )
        seen_hashes = set()
        for r in records:
            h = dupe_hash(USER_ID, r['date'], r['amount'], r.get('merchant'))
            if h in seen_hashes:
                skipped += 1
                continue
            seen_hashes.add(h)
            merchant_norm = (r.get('merchant') or '').strip().lower()
            amount_cents = int(round(float(r['amount']) * 100))
            exists = conn.execute(
                """
                SELECT 1 FROM transactions
                WHERE user_id = ? AND date = ?
                  AND CAST(ROUND(amount * 100) AS INTEGER) = ?
                  AND LOWER(COALESCE(merchant, '')) = ?
                LIMIT 1
                """,
                (USER_ID, r['date'], amount_cents, merchant_norm),
            ).fetchone()
            if exists:
                skipped += 1
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    id, user_id, account_id, date, amount, merchant, description,
                    category, category_source, category_provenance,
                    is_recurring, mcc, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r['id'], r['user_id'], r.get(
                        'account_id'), r['date'], r['amount'], r.get('merchant'),
                    r.get('description'), r.get('category'), r.get(
                        'category_source'), r.get('category_provenance'),
                    r.get('is_recurring', False), r.get(
                        'mcc'), r.get('source', 'csv'),
                ),
            )
            inserted += 1
    print('Inserted', inserted, 'skipped', skipped)

    print('Training model for', USER_ID)
    with get_connection() as conn:
        info = train_for_user(conn, USER_ID, min_per_class=1)
    print('Train info:', info)
    p = model_path(USER_ID)
    print('Model path exists?', p.exists(), p)
    print('Done')
