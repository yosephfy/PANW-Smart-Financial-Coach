from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, date
from collections import defaultdict

from .. import db as db_mod
from ..utils.auth import current_username
from ..services import subscriptions_service as svc


router = APIRouter(tags=["subscriptions"])


class SubscriptionAnalyticsResponse(BaseModel):
    total_subscriptions: int
    active_subscriptions: int
    paused_subscriptions: int
    canceled_subscriptions: int
    monthly_total: float
    yearly_projected: float
    avg_subscription_cost: float
    subscription_by_status: List[Dict[str, Any]]
    subscription_by_cadence: List[Dict[str, Any]]
    monthly_trends: List[Dict[str, Any]]
    top_subscriptions: List[Dict[str, Any]]
    cost_distribution: List[Dict[str, Any]]
    trial_conversions: int
    price_increases: int
    recent_changes: List[Dict[str, Any]]


@router.get("/subscriptions/analytics/{user_id}", response_model=SubscriptionAnalyticsResponse)
def get_subscription_analytics(user_id: str):
    """Get comprehensive subscription analytics for a user."""
    with db_mod.get_connection() as conn:
        # Get all subscriptions
        subs = conn.execute(
            """
            SELECT merchant, avg_amount, cadence, last_seen, status, 
                   price_change_pct, COALESCE(trial_converted, 0) as trial_converted,
                   COALESCE(created_at, datetime('now')) as created_at
            FROM subscriptions
            WHERE user_id = ?
            ORDER BY avg_amount DESC
            """,
            (user_id,),
        ).fetchall()

        subscriptions = [dict(row) for row in subs]

        # Calculate basic metrics
        total_subscriptions = len(subscriptions)
        active_count = sum(1 for s in subscriptions if s['status'] == 'active')
        paused_count = sum(1 for s in subscriptions if s['status'] == 'paused')
        canceled_count = sum(
            1 for s in subscriptions if s['status'] == 'canceled')

        # Calculate monthly total (only active subscriptions)
        monthly_total = 0.0
        for s in subscriptions:
            if s['status'] == 'active':
                if s['cadence'] == 'monthly':
                    monthly_total += s['avg_amount']
                elif s['cadence'] == 'weekly':
                    monthly_total += s['avg_amount'] * \
                        4.33  # Average weeks per month
                elif s['cadence'] == 'yearly':
                    monthly_total += s['avg_amount'] / 12

        yearly_projected = monthly_total * 12
        avg_subscription_cost = monthly_total / max(active_count, 1)

        # Status breakdown
        status_breakdown = [
            {"name": "Active", "value": active_count, "amount": sum(
                s['avg_amount'] for s in subscriptions if s['status'] == 'active')},
            {"name": "Paused", "value": paused_count, "amount": sum(
                s['avg_amount'] for s in subscriptions if s['status'] == 'paused')},
            {"name": "Canceled", "value": canceled_count, "amount": sum(
                s['avg_amount'] for s in subscriptions if s['status'] == 'canceled')}
        ]

        # Cadence breakdown
        cadence_counts = defaultdict(int)
        cadence_amounts = defaultdict(float)
        for s in subscriptions:
            if s['status'] == 'active':  # Only active subscriptions
                cadence_counts[s['cadence']] += 1
                cadence_amounts[s['cadence']] += s['avg_amount']

        cadence_breakdown = [
            {"name": cadence.capitalize(), "count": count,
             "amount": cadence_amounts[cadence]}
            for cadence, count in cadence_counts.items()
        ]

        # Get monthly trends from transaction history
        monthly_trends = []
        trend_data = conn.execute(
            """
            SELECT strftime('%Y-%m', date) as month, 
                   SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as subscription_spending
            FROM transactions t
            JOIN subscriptions s ON LOWER(t.merchant) = LOWER(s.merchant) AND t.user_id = s.user_id
            WHERE t.user_id = ? AND t.amount < 0
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month DESC
            LIMIT 12
            """,
            (user_id,),
        ).fetchall()

        for row in trend_data:
            monthly_trends.append({
                "month": row['month'],
                "amount": float(row['subscription_spending'])
            })

        # Top subscriptions by cost
        top_subscriptions = [
            {
                "merchant": s['merchant'],
                "amount": s['avg_amount'],
                "cadence": s['cadence'],
                "status": s['status']
            }
            for s in subscriptions[:10]
        ]

        # Cost distribution ranges
        cost_ranges = [(0, 10), (10, 25), (25, 50),
                       (50, 100), (100, float('inf'))]
        cost_distribution = []
        for min_cost, max_cost in cost_ranges:
            count = sum(1 for s in subscriptions
                        if min_cost <= s['avg_amount'] < max_cost and s['status'] == 'active')
            range_name = f"${min_cost}-${max_cost}" if max_cost != float(
                'inf') else f"${min_cost}+"
            cost_distribution.append({"range": range_name, "count": count})

        # Additional metrics
        trial_conversions = sum(
            1 for s in subscriptions if s['trial_converted'])
        price_increases = sum(
            1 for s in subscriptions if s['price_change_pct'] and s['price_change_pct'] > 0)

        # Recent changes (subscriptions with recent activity)
        recent_changes = []
        for s in subscriptions:
            try:
                last_seen_date = datetime.fromisoformat(s['last_seen']).date()
                days_ago = (date.today() - last_seen_date).days
                if days_ago <= 30:  # Last 30 days
                    recent_changes.append({
                        "merchant": s['merchant'],
                        "status": s['status'],
                        "days_ago": days_ago,
                        "amount": s['avg_amount']
                    })
            except:
                pass

        recent_changes.sort(key=lambda x: x['days_ago'])

        return SubscriptionAnalyticsResponse(
            total_subscriptions=total_subscriptions,
            active_subscriptions=active_count,
            paused_subscriptions=paused_count,
            canceled_subscriptions=canceled_count,
            monthly_total=round(monthly_total, 2),
            yearly_projected=round(yearly_projected, 2),
            avg_subscription_cost=round(avg_subscription_cost, 2),
            subscription_by_status=status_breakdown,
            subscription_by_cadence=cadence_breakdown,
            monthly_trends=monthly_trends,
            top_subscriptions=top_subscriptions,
            cost_distribution=cost_distribution,
            trial_conversions=trial_conversions,
            price_increases=price_increases,
            recent_changes=recent_changes[:10]  # Limit to 10 most recent
        )


class DetectRequest(BaseModel):
    user_id: str | None = None


@router.post("/subscriptions/detect")
def subscriptions_detect(request: Request, body: DetectRequest):
    uid = body.user_id or current_username(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_authenticated")
    with db_mod.get_connection() as conn:
        return svc.detect_and_upsert(conn, uid)


@router.get("/users/{user_id}/subscriptions")
def list_subscriptions(user_id: str, limit: int = Query(100, ge=1, le=500)):
    with db_mod.get_connection() as conn:
        return svc.list_for_user(conn, user_id, limit)


# Removed cookie-based "me" route; use /users/{user_id}/subscriptions


class TransactionSubscriptionRequest(BaseModel):
    user_id: str
    transaction_id: str


@router.post("/subscriptions/transaction/check")
def check_transaction_subscription_impact(body: TransactionSubscriptionRequest):
    """Check if a specific transaction impacts subscription detection."""
    with db_mod.get_connection() as conn:
        # Get the transaction
        tx = conn.execute(
            """
            SELECT id, user_id, account_id, date, amount, merchant, description,
                   category, category_source, category_provenance, is_recurring, mcc, source
            FROM transactions
            WHERE user_id = ? AND id = ?
            """,
            (body.user_id, body.transaction_id),
        ).fetchone()

        if not tx:
            raise HTTPException(
                status_code=404, detail="transaction_not_found")

        from ..services.transaction_subscription_service import detect_transaction_subscription_updates
        return detect_transaction_subscription_updates(conn, body.user_id, dict(tx))


class SubscriptionUpdateRequest(BaseModel):
    status: str
    user_id: str


@router.patch("/subscriptions/{merchant}")
def update_subscription_status(merchant: str, request: Request, body: SubscriptionUpdateRequest):
    u = (body.user_id or "").strip()
    if not u:
        raise HTTPException(status_code=400, detail="missing_user_id")
    status = (body.status or "").strip().lower()
    if status not in {"active", "paused", "canceled"}:
        raise HTTPException(status_code=400, detail="invalid_status")
    with db_mod.get_connection() as conn:
        changed = svc.update_status(conn, u, merchant, status)
        if changed == 0:
            raise HTTPException(
                status_code=404, detail="subscription_not_found")
    return {"merchant": merchant.strip().lower(), "status": status}
