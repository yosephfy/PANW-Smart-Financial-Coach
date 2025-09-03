#!/usr/bin/env python3
"""Ingest the sample CSV and print generated insights (convenience script)."""
import sys
from pathlib import Path

# Compute path to services/api/app so we can import local modules
repo = Path(__file__).resolve().parents[3]
app_dir = Path(__file__).resolve().parent.parent / 'app'
print('DEBUG app_dir:', app_dir)
sys.path.insert(0, str(app_dir))

from insights import generate_insights
from db import get_connection, init_db
from ingest import parse_csv_transactions


CSV_PATH = repo / 'data' / 'samples' / 'transactions_sample.csv'
USER = 'u_demo'

if __name__ == '__main__':
    init_db()
    content = CSV_PATH.read_bytes()
    recs = parse_csv_transactions(content, user_id=USER)
    print('Parsed', len(recs), 'records')
    with get_connection() as conn:
        conn.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (USER,))
        for r in recs:
            acc = r.get('account_id')
            if acc:
                conn.execute(
                    'INSERT OR IGNORE INTO accounts (id, user_id, name) VALUES (?, ?, ?)', (acc, USER, 'Imported'))
        for r in recs:
            conn.execute(
                """
                INSERT OR IGNORE INTO transactions (id, user_id, account_id, date, amount, merchant, description, category, category_source, category_provenance, is_recurring, mcc, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r['id'], r['user_id'], r.get('account_id'), r['date'], r['amount'], r.get('merchant'), r.get('description'), r.get('category'), r.get(
                        'category_source'), r.get('category_provenance'), r.get('is_recurring', False), r.get('mcc'), r.get('source', 'csv')
                ),
            )
    with get_connection() as conn:
        items = generate_insights(conn, USER)
        print('\nGenerated insights:')
        import json
        print(json.dumps(items, indent=2))
