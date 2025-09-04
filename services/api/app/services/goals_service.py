from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3

from ..goals import create_goal as _create_goal, list_goals as _list_goals, evaluate_goal as _evaluate_goal
from datetime import date, datetime
import hashlib


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


# --- Contributions ---

def _contrib_id(goal_id: str, when: str, amount: float) -> str:
    raw = f"{goal_id}|{when}|{amount}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def add_contribution(conn: sqlite3.Connection, goal_id: str, amount: float, when: Optional[str] = None) -> Dict:
    when = when or date.today().isoformat()
    cid = _contrib_id(goal_id, when, amount)
    conn.execute(
        "INSERT OR REPLACE INTO goal_contributions (id, goal_id, date, amount) VALUES (?, ?, ?, ?)",
        (cid, goal_id, when, amount),
    )
    # Auto-mark milestones and achieved
    row = conn.execute("SELECT user_id, target_amount FROM goals WHERE id = ?", (goal_id,)).fetchone()
    user_id = row["user_id"] if row else None
    target = float(row["target_amount"] or 0.0) if row else 0.0
    total = total_contributions(conn, goal_id)
    # milestones
    mrows = conn.execute("SELECT id, target_amount, hit_at FROM goal_milestones WHERE goal_id = ?", (goal_id,)).fetchall()
    for m in mrows:
        if not m["hit_at"] and total >= float(m["target_amount"] or 0.0):
            conn.execute("UPDATE goal_milestones SET hit_at = CURRENT_TIMESTAMP WHERE id = ?", (m["id"],))
    # achieved
    if target and total >= target:
        conn.execute("UPDATE goals SET status = 'achieved', achieved_at = CURRENT_TIMESTAMP WHERE id = ?", (goal_id,))
    return {"id": cid, "goal_id": goal_id, "date": when, "amount": amount}


def list_contributions(conn: sqlite3.Connection, goal_id: str) -> List[Dict]:
    rows = conn.execute(
        "SELECT id, date, amount FROM goal_contributions WHERE goal_id = ? ORDER BY date DESC",
        (goal_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def total_contributions(conn: sqlite3.Connection, goal_id: str) -> float:
    r = conn.execute("SELECT SUM(amount) AS s FROM goal_contributions WHERE goal_id = ?", (goal_id,)).fetchone()
    return float(r["s"] or 0.0)


def add_milestone(conn: sqlite3.Connection, goal_id: str, name: str, target_amount: float) -> Dict:
    raw = f"{goal_id}|{name}|{target_amount}"
    mid = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    conn.execute(
        "INSERT OR REPLACE INTO goal_milestones (id, goal_id, name, target_amount) VALUES (?, ?, ?, ?)",
        (mid, goal_id, name, target_amount),
    )
    return {"id": mid, "goal_id": goal_id, "name": name, "target_amount": target_amount}


def list_milestones(conn: sqlite3.Connection, goal_id: str) -> List[Dict]:
    rows = conn.execute(
        "SELECT id, name, target_amount, hit_at FROM goal_milestones WHERE goal_id = ? ORDER BY target_amount",
        (goal_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def fund_auto(conn: sqlite3.Connection, user_id: str, amount: float, strategy: str = "proportional") -> Dict:
    # Get active goals
    goals = conn.execute(
        "SELECT id, target_amount FROM goals WHERE user_id = ? AND (status IS NULL OR status = 'active')",
        (user_id,),
    ).fetchall()
    if not goals or amount <= 0:
        return {"user_id": user_id, "allocated": [], "total": 0.0}
    gaps = []
    for g in goals:
        gid = g["id"]
        target = float(g["target_amount"] or 0.0)
        contributed = total_contributions(conn, gid)
        gap = max(target - contributed, 0.0)
        if gap > 0:
            gaps.append((gid, gap))
    if not gaps:
        return {"user_id": user_id, "allocated": [], "total": 0.0}
    total_gap = sum(g for _, g in gaps)
    remaining = amount
    allocations: List[Dict] = []
    for gid, gap in gaps:
        share = amount * (gap / total_gap) if total_gap > 0 else 0.0
        alloc = round(min(share, gap, remaining), 2)
        if alloc <= 0:
            continue
        add_contribution(conn, gid, alloc)
        allocations.append({"goal_id": gid, "amount": alloc})
        remaining = round(remaining - alloc, 2)
        if remaining <= 0:
            break
    return {"user_id": user_id, "allocated": allocations, "total": round(amount - remaining, 2)}
