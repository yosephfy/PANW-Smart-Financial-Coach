#!/usr/bin/env python3
"""Test per-transaction subscription detection."""

from datetime import date, timedelta
import uuid
from app.services.transaction_subscription_service import (
    detect_transaction_subscription_updates,
    generate_subscription_insights_for_transaction
)
from app.db import get_connection, init_db
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


def create_test_transaction(user_id: str, days_ago: int, amount: float, merchant: str) -> dict:
    """Helper to create a test transaction."""
    tx_date = (date.today() - timedelta(days=days_ago)).isoformat()
    return {
        'id': uuid.uuid4().hex,
        'user_id': user_id,
        'date': tx_date,
        'amount': amount,
        'merchant': merchant,
        'description': f'{merchant} subscription',
        'category': 'subscriptions',
        'source': 'test'
    }


def insert_transaction(conn, transaction):
    """Insert a transaction into the database."""
    conn.execute(
        """
        INSERT OR REPLACE INTO transactions (
            id, user_id, account_id, date, amount, merchant, description,
            category, category_source, category_provenance, is_recurring, mcc, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction['id'], transaction['user_id'], None,
            transaction['date'], transaction['amount'], transaction.get(
                'merchant'),
            transaction.get('description'), transaction.get(
                'category'), None, None,
            False, None, transaction.get('source')
        )
    )


def main():
    print("Testing per-transaction subscription detection...")

    # Initialize database
    init_db()

    user_id = "test_subscription_user"

    with get_connection() as conn:
        # Clean up previous test data
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM insights WHERE user_id = ?", (user_id,))
        conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))

        # Create a series of subscription-like transactions for Netflix
        netflix_transactions = [
            create_test_transaction(user_id, 90, -15.99, "Netflix"),
            create_test_transaction(user_id, 60, -15.99, "Netflix"),
            create_test_transaction(user_id, 30, -15.99, "Netflix"),
        ]

        print("\n1. Adding first two Netflix transactions...")
        for tx in netflix_transactions[:2]:
            insert_transaction(conn, tx)
            result = detect_transaction_subscription_updates(conn, user_id, tx)
            print(f"   Transaction {tx['date']}: Action = {result['action']}")

        print("\n2. Adding third Netflix transaction (should detect subscription)...")
        third_tx = netflix_transactions[2]
        insert_transaction(conn, third_tx)
        result = detect_transaction_subscription_updates(
            conn, user_id, third_tx)
        print(
            f"   Transaction {third_tx['date']}: Action = {result['action']}")

        if result['subscription']:
            sub = result['subscription']
            print(
                f"   Detected: ${sub['avg_amount']:.2f} {sub['cadence']} subscription")

        # Generate subscription insights
        insights = generate_subscription_insights_for_transaction(
            conn, user_id, third_tx, result)
        print(f"   Generated {len(insights)} subscription insights")

        for insight in insights:
            print(f"   - {insight['type']}: {insight['title']}")

        print("\n3. Adding Netflix transaction with price increase...")
        price_increase_tx = create_test_transaction(
            user_id, 0, -17.99, "Netflix")
        insert_transaction(conn, price_increase_tx)
        result = detect_transaction_subscription_updates(
            conn, user_id, price_increase_tx)
        print(
            f"   Transaction {price_increase_tx['date']}: Action = {result['action']}")

        if result.get('subscription'):
            sub = result['subscription']
            price_change = sub.get('price_change_pct', 0)
            print(f"   Price change: {price_change:+.1f}%")

        # Generate insights for price change
        insights = generate_subscription_insights_for_transaction(
            conn, user_id, price_increase_tx, result)
        print(f"   Generated {len(insights)} price change insights")

        for insight in insights:
            print(f"   - {insight['type']}: {insight['title']}")

        print("\n4. Testing with a different service (Spotify)...")
        spotify_tx = create_test_transaction(user_id, 0, -12.99, "Spotify")
        insert_transaction(conn, spotify_tx)
        result = detect_transaction_subscription_updates(
            conn, user_id, spotify_tx)
        print(
            f"   Spotify transaction: Action = {result['action']} (expected: none, not enough history)")

        print("\nTest completed!")


if __name__ == '__main__':
    main()
