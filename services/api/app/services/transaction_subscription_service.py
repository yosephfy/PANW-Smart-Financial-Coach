from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3
from datetime import date, timedelta

from ..subscriptions import detect_subscriptions_for_user, upsert_subscriptions, SubscriptionCandidate
from ..services.subscriptions_service import detect_and_upsert


def detect_transaction_subscription_updates(conn: sqlite3.Connection, user_id: str, transaction: Dict) -> Dict:
    """
    Check if a newly added transaction affects subscription detection.
    Now automatically processes and saves any detected subscriptions.
    """
    result = {
        "merchant": transaction.get("merchant", ""),
        "subscription_detected": False,
        "subscription_updated": False,
        "subscription": None,
        "action": "none",
        "all_subscriptions_processed": False
    }

    # Only process expenses with merchants
    tx_amount = float(transaction.get("amount", 0))
    tx_merchant = transaction.get("merchant", "").strip().lower()

    if tx_amount >= 0 or not tx_merchant:
        return result

    # Get all transactions for this merchant to check patterns
    merchant_transactions = conn.execute(
        """
        SELECT date, amount
        FROM transactions
        WHERE user_id = ? AND LOWER(COALESCE(merchant,'')) = ? AND amount < 0
        ORDER BY date ASC
        """,
        (user_id, tx_merchant)
    ).fetchall()

    # Check if this merchant already has a detected subscription
    existing_sub = conn.execute(
        """
        SELECT merchant, cadence, avg_amount, last_seen, status, trial_converted, price_change_pct
        FROM subscriptions 
        WHERE user_id = ? AND LOWER(merchant) = ?
        """,
        (user_id, tx_merchant)
    ).fetchone()

    # If we have 2+ transactions for this merchant, check for subscription patterns
    if len(merchant_transactions) >= 2:
        dates = []
        amounts = []

        for row in merchant_transactions:
            try:
                tx_date = date.fromisoformat(row["date"])
                dates.append(tx_date)
                amounts.append(abs(float(row["amount"])))
            except Exception:
                continue

        # Quick subscription-like pattern detection
        if len(dates) >= 2:
            intervals = [
                (dates[i] - dates[i-1]).days for i in range(1, len(dates))]

            # Look for subscription-like intervals (weekly, monthly patterns)
            subscription_like_intervals = [
                i for i in intervals
                if (6 <= i <= 9) or (25 <= i <= 35) or (90 <= i <= 100) or (360 <= i <= 370)
            ]

            # Check amount consistency
            from statistics import median
            if amounts:
                med_amount = median(amounts)
                consistent_amounts = sum(
                    1 for amt in amounts
                    if abs(amt - med_amount) <= max(3.0, 0.15 * med_amount)
                )
                amount_consistency = consistent_amounts / len(amounts)

                # If patterns suggest subscription behavior, run full detection
                pattern_strength = len(
                    subscription_like_intervals) / max(1, len(intervals))
                is_subscription_candidate = (
                    (len(dates) >= 3 and pattern_strength >= 0.6 and amount_consistency >= 0.7) or
                    (len(dates) >= 2 and pattern_strength >=
                     0.8 and amount_consistency >= 0.8)
                )

                # Also check if this merchant has been flagged as subscription in categories
                tx_category = transaction.get("category", "").lower()
                is_subscription_category = "subscription" in tx_category

                if is_subscription_candidate or is_subscription_category or existing_sub:
                    try:
                        # Run comprehensive subscription detection for this user
                        print(
                            f"Running subscription detection triggered by {tx_merchant} transaction")
                        all_subs = detect_subscriptions_for_user(conn, user_id)

                        if all_subs:
                            # Automatically upsert all detected subscriptions
                            inserted, updated = upsert_subscriptions(
                                conn, user_id, all_subs)
                            result["all_subscriptions_processed"] = True

                            # Find if our specific merchant was detected
                            merchant_sub = None
                            for sub in all_subs:
                                if sub.merchant.lower() == tx_merchant:
                                    merchant_sub = sub
                                    break

                            if merchant_sub:
                                was_new = not existing_sub
                                result.update({
                                    "subscription_detected": was_new,
                                    "subscription_updated": not was_new,
                                    "subscription": merchant_sub.__dict__,
                                    "action": "detected" if was_new else "updated"
                                })

                                print(
                                    f"Subscription {'detected' if was_new else 'updated'} for {tx_merchant}: ${merchant_sub.avg_amount:.2f} {merchant_sub.cadence}")

                            # Log the overall results
                            print(
                                f"Subscription detection: {len(all_subs)} total subscriptions, {inserted} new, {updated} updated")

                    except Exception as e:
                        print(f"Failed to run subscription detection: {e}")

                # Also check for price changes if subscription exists
                elif existing_sub and len(amounts) > 0:
                    current_amount = amounts[-1]  # Most recent amount
                    existing_avg = float(existing_sub["avg_amount"])

                    # If amount changed significantly, re-run detection
                    if abs(current_amount - existing_avg) > max(3.0, 0.15 * existing_avg):
                        try:
                            print(
                                f"Price change detected for {tx_merchant}: ${current_amount:.2f} vs ${existing_avg:.2f}")
                            all_subs = detect_subscriptions_for_user(
                                conn, user_id)
                            merchant_sub = None

                            for sub in all_subs:
                                if sub.merchant.lower() == tx_merchant:
                                    merchant_sub = sub
                                    break

                            if merchant_sub:
                                inserted, updated = upsert_subscriptions(
                                    conn, user_id, [merchant_sub])
                                result.update({
                                    "subscription_detected": False,
                                    "subscription_updated": True,
                                    "subscription": merchant_sub.__dict__,
                                    "action": "amount_updated"
                                })

                        except Exception as e:
                            print(
                                f"Failed to update subscription for {tx_merchant}: {e}")

    return result


def generate_subscription_insights_for_transaction(conn: sqlite3.Connection, user_id: str, transaction: Dict, subscription_update: Dict) -> List[Dict]:
    """Generate insights related to subscription changes from a transaction."""
    insights = []

    if not subscription_update.get("subscription"):
        return insights

    subscription = subscription_update["subscription"]
    action = subscription_update["action"]
    tx_merchant = transaction.get("merchant", "")
    tx_amount = abs(float(transaction.get("amount", 0)))

    from ..insights import _transaction_insight_id
    import json

    if action == "detected":
        # New subscription detected
        insights.append({
            "id": _transaction_insight_id(user_id, "subscription_detected", tx_merchant.lower().replace(" ", "_"), transaction["id"]),
            "user_id": user_id,
            "type": "subscription_detected",
            "title": f"New subscription detected: {tx_merchant.title()}",
            "body": f"${subscription['avg_amount']:.2f} {subscription['cadence']} subscription detected based on your recent transactions.",
            "severity": "info",
            "data_json": json.dumps({
                "transaction_id": transaction["id"],
                "merchant": tx_merchant,
                "cadence": subscription["cadence"],
                "avg_amount": subscription["avg_amount"],
                "trial_converted": subscription.get("trial_converted", False),
            }),
        })

    elif action == "amount_updated":
        # Price change detected
        price_change = subscription.get("price_change_pct")
        if price_change and abs(price_change) >= 10:  # 10% or more change
            direction = "increase" if price_change > 0 else "decrease"
            severity = "warn" if price_change > 0 else "info"

            insights.append({
                "id": _transaction_insight_id(user_id, "subscription_price_change", tx_merchant.lower().replace(" ", "_"), transaction["id"]),
                "user_id": user_id,
                "type": "subscription_price_change",
                "title": f"{tx_merchant.title()} price {direction}",
                "body": f"${tx_amount:.2f} vs usual ${subscription['avg_amount']:.2f} ({price_change:+.1f}% {direction}).",
                "severity": severity,
                "data_json": json.dumps({
                    "transaction_id": transaction["id"],
                    "merchant": tx_merchant,
                    "old_amount": subscription["avg_amount"],
                    "new_amount": tx_amount,
                    "price_change_pct": price_change,
                }),
            })

    # Check for trial conversion
    if subscription.get("trial_converted") and action in ["detected", "updated"]:
        insights.append({
            "id": _transaction_insight_id(user_id, "trial_converted", tx_merchant.lower().replace(" ", "_"), transaction["id"]),
            "user_id": user_id,
            "type": "trial_converted",
            "title": f"{tx_merchant.title()} trial ended",
            "body": f"Free trial converted to paid ${subscription['avg_amount']:.2f} {subscription['cadence']} subscription.",
            "severity": "info",
            "data_json": json.dumps({
                "transaction_id": transaction["id"],
                "merchant": tx_merchant,
                "avg_amount": subscription["avg_amount"],
                "cadence": subscription["cadence"],
            }),
        })

    return insights
