from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from .. import db as db_mod
from ..repositories import transactions_repo


router = APIRouter(tags=["transactions"])


class TransactionAnalyticsResponse(BaseModel):
    total_income: float
    total_expenses: float
    net_cash_flow: float
    transaction_count: int
    recurring_count: int
    avg_transaction_size: float
    top_merchants: List[Dict[str, Any]]
    category_breakdown: List[Dict[str, Any]]
    account_breakdown: List[Dict[str, Any]]
    daily_trend: List[Dict[str, Any]]


@router.get("/transactions/analytics", response_model=TransactionAnalyticsResponse)
def get_transaction_analytics(
    user_id: str = Query(..., description="User ID"),
    account_id: Optional[str] = Query(
        None, description="Optional account filter"),
    days: Optional[int] = Query(
        None, description="Days back to analyze (default: all time)"),
):
    """
    Get comprehensive transaction analytics for a user.
    This endpoint calculates analytics on ALL transactions, not affected by UI pagination limits.
    """
    try:
        with db_mod.get_connection() as conn:
            # Build query filters
            filters = {"user_id": user_id}
            if account_id:
                filters["account_id"] = account_id

            # Date filter for recent analysis
            if days:
                cutoff_date = (datetime.now() -
                               timedelta(days=days)).isoformat()
                date_filter = f" AND date >= '{cutoff_date}'"
            else:
                date_filter = ""

            # Get all transactions for this user
            query = f"""
                SELECT id, user_id, account_id, date, amount, merchant, 
                       description, category, is_recurring, mcc, source
                FROM transactions 
                WHERE user_id = ?{date_filter}
                ORDER BY date DESC
            """

            cursor = conn.execute(query, (user_id,))
            transactions = [dict(row) for row in cursor.fetchall()]

            if not transactions:
                # Return empty analytics
                return TransactionAnalyticsResponse(
                    total_income=0.0,
                    total_expenses=0.0,
                    net_cash_flow=0.0,
                    transaction_count=0,
                    recurring_count=0,
                    avg_transaction_size=0.0,
                    top_merchants=[],
                    category_breakdown=[],
                    account_breakdown=[],
                    daily_trend=[]
                )

            # Calculate basic analytics
            total_income = sum(t['amount']
                               for t in transactions if t['amount'] > 0)
            total_expenses = sum(abs(t['amount'])
                                 for t in transactions if t['amount'] < 0)
            net_cash_flow = total_income - total_expenses
            transaction_count = len(transactions)
            recurring_count = sum(1 for t in transactions if t['is_recurring'])
            avg_transaction_size = sum(abs(
                t['amount']) for t in transactions) / transaction_count if transaction_count > 0 else 0

            # Top merchants analysis (expenses only)
            merchant_spending = defaultdict(lambda: {'amount': 0, 'count': 0})
            for t in transactions:
                if t['amount'] < 0:  # Only expenses
                    merchant = t['merchant'] or 'Unknown'
                    merchant_spending[merchant]['amount'] += abs(t['amount'])
                    merchant_spending[merchant]['count'] += 1

            top_merchants = [
                {
                    'name': merchant,
                    'amount': data['amount'],
                    'value': data['amount'],  # For chart compatibility
                    'count': data['count'],
                    'avgAmount': data['amount'] / data['count']
                }
                for merchant, data in merchant_spending.items()
            ]
            top_merchants.sort(key=lambda x: x['amount'], reverse=True)
            top_merchants = top_merchants[:10]

            # Category breakdown
            category_spending = defaultdict(float)
            for t in transactions:
                if t['amount'] < 0:  # Only expenses
                    category = t['category'] or 'Uncategorized'
                    category_spending[category] += abs(t['amount'])

            category_breakdown = [
                {'category': cat, 'amount': amount, 'value': amount}
                for cat, amount in category_spending.items()
            ]
            category_breakdown.sort(key=lambda x: x['amount'], reverse=True)

            # Account breakdown
            account_stats = defaultdict(
                lambda: {'income': 0, 'expenses': 0, 'count': 0})
            for t in transactions:
                acc_id = t['account_id'] or 'Unknown'
                account_stats[acc_id]['count'] += 1
                if t['amount'] > 0:
                    account_stats[acc_id]['income'] += t['amount']
                else:
                    account_stats[acc_id]['expenses'] += abs(t['amount'])

            account_breakdown = [
                {
                    'account': acc_id,
                    'income': stats['income'],
                    'expenses': stats['expenses'],
                    'net': stats['income'] - stats['expenses'],
                    'count': stats['count']
                }
                for acc_id, stats in account_stats.items()
            ]

            # Daily trend (last 30 days if no specific day filter, or all available days)
            trend_days = days if days and days <= 30 else 30
            daily_amounts = defaultdict(
                lambda: {'income': 0, 'expenses': 0, 'net': 0})

            for t in transactions:
                date_key = t['date'][:10]  # YYYY-MM-DD
                if t['amount'] > 0:
                    daily_amounts[date_key]['income'] += t['amount']
                else:
                    daily_amounts[date_key]['expenses'] += abs(t['amount'])
                daily_amounts[date_key]['net'] = daily_amounts[date_key]['income'] - \
                    daily_amounts[date_key]['expenses']

            # Get last N days
            sorted_dates = sorted(daily_amounts.keys(), reverse=True)[
                :trend_days]
            daily_trend = [
                {
                    'date': date,
                    'income': daily_amounts[date]['income'],
                    'expenses': daily_amounts[date]['expenses'],
                    'net': daily_amounts[date]['net']
                }
                for date in reversed(sorted_dates)  # Chronological order
            ]

            return TransactionAnalyticsResponse(
                total_income=total_income,
                total_expenses=total_expenses,
                net_cash_flow=net_cash_flow,
                transaction_count=transaction_count,
                recurring_count=recurring_count,
                avg_transaction_size=avg_transaction_size,
                top_merchants=top_merchants,
                category_breakdown=category_breakdown,
                account_breakdown=account_breakdown,
                daily_trend=daily_trend
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate analytics: {str(e)}")
