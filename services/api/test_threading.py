#!/usr/bin/env python3
"""Test the threaded LLM insights system."""

import time
from app.services.insights_service import generate_transaction_insights_and_upsert
from app.db import get_connection, init_db
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


# Sample transaction that should trigger multiple insights
test_transaction = {
    'id': 'test_threading_123',
    'user_id': 'u_demo',
    'date': '2025-09-04',  # Today's date
    'amount': -250.0,  # Large expense to trigger spikes
    'merchant': 'fancy steakhouse',
    'category': 'restaurants',
    'description': 'expensive dinner',
    'account_id': 'test_account',
    'source': 'test'
}


def main():
    print("Testing threaded LLM insights generation...")

    # Initialize database
    init_db()

    # Time the insight generation
    start_time = time.time()

    with get_connection() as conn:
        # Insert the test transaction first
        conn.execute(
            """
            INSERT OR REPLACE INTO transactions (
                id, user_id, account_id, date, amount, merchant, description,
                category, category_source, category_provenance, is_recurring, mcc, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_transaction['id'], test_transaction['user_id'], test_transaction.get(
                    'account_id'),
                test_transaction['date'], test_transaction['amount'], test_transaction.get(
                    'merchant'),
                test_transaction.get('description'), test_transaction.get(
                    'category'), None, None,
                False, None, test_transaction.get('source')
            )
        )

        # Generate insights with threading
        insights = generate_transaction_insights_and_upsert(
            conn, test_transaction['user_id'], test_transaction)

    end_time = time.time()
    processing_time = end_time - start_time

    print(
        f"Generated {len(insights)} insights in {processing_time:.2f} seconds")
    print("\nInsights generated:")
    for i, insight in enumerate(insights, 1):
        print(f"\n{i}. {insight['type']}: {insight['title']}")
        print(f"   Original: {insight['body']}")
        if insight.get('rewritten_title'):
            print(f"   LLM Title: {insight['rewritten_title']}")
        if insight.get('rewritten_body'):
            print(f"   LLM Body: {insight['rewritten_body']}")


if __name__ == '__main__':
    main()
