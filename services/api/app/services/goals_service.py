from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3

from ..goals import create_goal as _create_goal, list_goals as _list_goals, evaluate_goal as _evaluate_goal


def create(conn: sqlite3.Connection, user_id: str, name: str, target_amount: float, target_date: str) -> Dict:
    return _create_goal(conn, user_id, name, target_amount, target_date)


def list_for_user(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    return _list_goals(conn, user_id)


def evaluate(conn: sqlite3.Connection, goal_id: str) -> Dict:
    return _evaluate_goal(conn, goal_id)


def update(conn: sqlite3.Connection, goal_id: str, *, name: Optional[str] = None, target_amount: Optional[float] = None, target_date: Optional[str] = None, status: Optional[str] = None) -> Dict:
    fields = []
    params = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if target_amount is not None:
        fields.append("target_amount = ?")
        params.append(target_amount)
    if target_date is not None:
        fields.append("target_date = ?")
        params.append(target_date)
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if not fields:
        raise ValueError("no_updates")
    params.append(goal_id)
    conn.execute(f"UPDATE goals SET {', '.join(fields)} WHERE id = ?", params)
    row = conn.execute("SELECT user_id, target_amount, target_date FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not row:
        raise KeyError("goal_not_found")
    try:
        plan = _evaluate_goal(conn, goal_id)
    except Exception:
        plan = None
    return {"id": goal_id, "plan": plan}

