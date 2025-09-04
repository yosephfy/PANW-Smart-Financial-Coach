from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import sqlite3
from .forecast import forecast_categories, forecast_net


DISCRETIONARY = {
    "coffee", "food_delivery", "fast_food", "restaurants", "shopping", "rideshare", "subscriptions"
}

# Max realistic cut percentages by category (behavioral elasticity)
MAX_CUT_PCT = {
    "subscriptions": 0.8,   # can cancel/trim
    "coffee": 0.6,
    "food_delivery": 0.5,
    "fast_food": 0.5,
    "restaurants": 0.35,
    "shopping": 0.4,
    "rideshare": 0.3,
}


def goal_id(user_id: str, name: str, target_amount: float, target_date: str) -> str:
    raw = f"{user_id}|{name}|{target_amount}|{target_date}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _months_between(start: date, end: date) -> int:
    if end <= start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + (1 if end.day > start.day else 0)


def _monthly_net_series(conn: sqlite3.Connection, user_id: str, months: int = 3) -> List[Tuple[str, float]]:
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date) AS ym,
               SUM(amount) AS net
        FROM transactions
        WHERE user_id = ?
        GROUP BY ym
        ORDER BY ym DESC
        LIMIT ?
        """,
        (user_id, months),
    ).fetchall()
    return [(r["ym"], float(r["net"] or 0.0)) for r in rows]


def _avg_monthly_net(conn: sqlite3.Connection, user_id: str, months: int = 3) -> float:
    series = _monthly_net_series(conn, user_id, months)
    if not series:
        return 0.0
    vals = [v for _, v in series]
    return sum(vals) / len(vals)


def _forecasted_disc_spend(conn: sqlite3.Connection, user_id: str) -> Dict[str, Dict[str, float | str]]:
    """Return map of category -> { amount, model } using category forecasts.

    amount: forecasted next-month spend
    model:  provenance of forecast ('ridge' | 'weighted')
    """
    fc = forecast_categories(conn, user_id, months_history=6, top_k=50)
    out: Dict[str, Dict[str, float | str]] = {}
    for item in fc.get("forecasts", []):
        cat = (item.get("category") or "").lower()
        if cat in DISCRETIONARY:
            out[cat] = {
                "amount": float(item.get("forecast_next_month") or 0.0),
                "model": str(item.get("model") or "weighted"),
            }
    return out


def compute_goal_plan(conn: sqlite3.Connection, user_id: str, target_amount: float, target_date: str) -> Dict:
    today = date.today()
    try:
        td = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        # try YYYY/MM/DD
        td = datetime.strptime(target_date.replace("/", "-"), "%Y-%m-%d").date()

    months_left = max(_months_between(today, td), 1)
    # Forecasted monthly surplus using ML/weighted net forecast
    net_fc = forecast_net(conn, user_id, months_history=6)
    current_surplus = float(net_fc.get("forecast_next_month", 0.0))
    # Required monthly saving to hit goal (assume starting at 0 saved for MVP)
    required_monthly = float(target_amount) / months_left
    gap = max(required_monthly - current_surplus, 0.0)

    # Suggest savings plan from forecasted discretionary categories using variable, realistic caps
    disc_spend = _forecasted_disc_spend(conn, user_id)
    # Compute potential per category = forecast * max_cut_pct
    potentials: List[Tuple[str, float, str, float]] = []  # (cat, forecast_amt, model, potential)
    total_potential = 0.0
    for cat, meta in disc_spend.items():
        amt = float(meta["amount"])  # forecasted next-month spend for category
        model = str(meta.get("model", "weighted"))
        max_pct = MAX_CUT_PCT.get(cat, 0.3)
        pot = round(amt * max_pct, 2)
        if pot > 0:
            potentials.append((cat, amt, model, pot))
            total_potential += pot
    # Rank by potential impact (largest first)
    potentials.sort(key=lambda x: x[3], reverse=True)

    plan: List[Dict] = []
    remaining = gap
    if remaining > 0 and total_potential > 0:
        # First pass: proportional allocation by potential
        for cat, amt, model, pot in potentials:
            share = pot / total_potential
            proposed = round(min(pot, remaining * share), 2)
            if proposed > 0:
                plan.append({
                    "category": cat,
                    "forecast_spend": round(amt, 2),
                    "suggested_cut": proposed,
                    "cut_pct": round(proposed / amt, 2) if amt > 0 else 0,
                    "forecast_model": model,
                    "max_cut_pct": MAX_CUT_PCT.get(cat, 0.3),
                })
        # Second pass: distribute any residual up to each category's remaining potential
        allocated = sum(p["suggested_cut"] for p in plan)
        residual = round(max(remaining - allocated, 0.0), 2)
        if residual > 0:
            for p, (_, _, _, pot) in zip(plan, potentials):
                if residual <= 0:
                    break
                remaining_cap = round(pot - p["suggested_cut"], 2)
                if remaining_cap <= 0:
                    continue
                add = round(min(remaining_cap, residual), 2)
                p["suggested_cut"] = round(p["suggested_cut"] + add, 2)
                p["cut_pct"] = round(p["suggested_cut"] / p["forecast_spend"], 2) if p["forecast_spend"] > 0 else 0
                residual = round(residual - add, 2)

    feasible = remaining <= total_potential + 1e-6 or gap <= total_potential + 1e-6
    shortfall = round(max(gap - total_potential, 0.0), 2)

    on_track = current_surplus >= required_monthly or remaining <= 0.01

    return {
        "target_date": td.isoformat(),
        "months_left": months_left,
        "current_surplus_monthly": round(current_surplus, 2),
        "required_monthly": round(required_monthly, 2),
        "gap": round(gap, 2),
        "on_track": on_track,
        "suggested_plan": plan,
        "total_potential": round(total_potential, 2),
        "feasible": bool(feasible),
        "shortfall": shortfall,
    }


# Convenience helpers used by API
def create_goal(conn: sqlite3.Connection, user_id: str, name: str, target_amount: float, target_date: str) -> Dict:
    gid = goal_id(user_id, name, target_amount, target_date)
    conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.execute(
        """
        INSERT OR REPLACE INTO goals (id, user_id, name, target_amount, target_date, status)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT status FROM goals WHERE id = ?), 'active'))
        """,
        (gid, user_id, name, target_amount, target_date, gid),
    )
    plan = compute_goal_plan(conn, user_id, target_amount, target_date)
    return {"id": gid, "user_id": user_id, "name": name, "target_amount": target_amount, "target_date": target_date, "plan": plan}


def list_goals(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    rows = conn.execute(
        "SELECT id, name, target_amount, target_date, monthly_target, status, created_at FROM goals WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    out: List[Dict] = []
    for r in rows:
        item = dict(r)
        if r["target_date"]:
            item["plan"] = compute_goal_plan(conn, user_id, float(r["target_amount"]), r["target_date"])  # type: ignore
        out.append(item)
    return out


def evaluate_goal(conn: sqlite3.Connection, goal_id_value: str) -> Dict:
    row = conn.execute("SELECT user_id, target_amount, target_date FROM goals WHERE id = ?", (goal_id_value,)).fetchone()
    if not row:
        raise ValueError("goal_not_found")
    return compute_goal_plan(conn, row["user_id"], float(row["target_amount"]), row["target_date"])  # type: ignore
