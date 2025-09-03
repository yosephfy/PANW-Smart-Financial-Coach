from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
import uuid


def create_goal(conn: sqlite3.Connection, user_id: str, name: str, target_amount: float, target_date: Optional[str] = None, monthly_target: Optional[float] = None) -> Dict:
    gid = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO goals (id, user_id, name, target_amount, target_date, monthly_target, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (gid, user_id, name, float(target_amount),
         target_date, monthly_target, 'active'),
    )
    return {"id": gid, "user_id": user_id, "name": name, "target_amount": float(target_amount), "target_date": target_date, "monthly_target": monthly_target, "status": "active"}


def list_goals(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT id, name, target_amount, target_date, monthly_target, status, monthly_target
        FROM goals
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _monthly_net_savings(conn: sqlite3.Connection, user_id: str, months: int = 6) -> List[Tuple[str, float]]:
    # Returns list of (ym, net_savings) where net = income - expenses (positive = saved)
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date) as ym,
          SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
          SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as expense
        FROM transactions
        WHERE user_id = ?
        GROUP BY ym
        ORDER BY ym DESC
        LIMIT ?
        """,
        (user_id, months * 2),
    ).fetchall()
    out: List[Tuple[str, float]] = []
    for r in rows[:months]:
        ym = r['ym']
        income = float(r['income'] or 0.0)
        expense = float(r['expense'] or 0.0)
        out.append((ym, income - expense))
    return out


def evaluate_goal(conn: sqlite3.Connection, goal_id: str) -> Dict:
    row = conn.execute(
        "SELECT id, user_id, name, target_amount, target_date, monthly_target FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not row:
        raise ValueError('goal_not_found')
    goal = dict(row)
    user_id = goal['user_id']

    # compute average monthly net savings over last 6 months
    months = _monthly_net_savings(conn, user_id, months=6)
    if months:
        avg = sum(v for _, v in months) / len(months)
    else:
        avg = 0.0

    target = float(goal['target_amount'])
    monthly_plan = goal.get('monthly_target')

    # simple heuristic: if monthly_target provided, use it; else use avg if positive
    if monthly_plan and float(monthly_plan) > 0:
        monthly_contrib = float(monthly_plan)
    else:
        monthly_contrib = float(avg)

    saved_rate = monthly_contrib

    # naive remaining calculation: assume starting from 0 saved toward goal
    # (could be enhanced to track current goal progress)
    if saved_rate <= 0:
        months_to_goal = None
        on_track = False
    else:
        import math
        months_to_goal = math.ceil(max(0.0, target) / saved_rate)
        on_track = True

    advice = []
    if not on_track:
        advice.append(
            'Your recent net savings are not positive. Consider trimming discretionary spend or adding an explicit monthly contribution to the goal.')
    else:
        advice.append(
            f'At ${saved_rate:.2f}/month you will reach ${target:.0f} in approximately {months_to_goal} months.')

    return {
        'goal': goal,
        'monthly_avg_savings': round(avg, 2),
        'monthly_plan_contribution': round(monthly_contrib, 2),
        'months_to_goal': months_to_goal,
        'on_track': on_track,
        'advice': advice,
    }
