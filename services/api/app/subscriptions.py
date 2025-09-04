from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from statistics import median
from typing import Iterable, List, Optional, Tuple
import hashlib

import sqlite3


@dataclass
class SubscriptionCandidate:
    merchant: str
    cadence: str  # monthly|weekly
    avg_amount: float
    last_seen: str  # ISO date
    price_change_pct: Optional[float]
    trial_converted: bool
    status: str  # active|paused


def _parse_date(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except Exception:
        # try common alternatives
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(d, fmt).date()
            except Exception:
                continue
    raise ValueError(f"Invalid date format: {d}")


def _intervals_in_days(dates: List[date]) -> List[int]:
    return [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]


def _amounts_stats(amounts: List[float]) -> Tuple[float, float]:
    # Return (median_abs, last_abs)
    abs_vals = [abs(a) for a in amounts]
    return (median(abs_vals), abs_vals[-1])


def _price_change_pct(median_abs: float, last_abs: float) -> Optional[float]:
    if median_abs <= 0:
        return None
    return round((last_abs - median_abs) / median_abs * 100.0, 2)


def _detect_cadence(intervals: List[int]) -> Optional[str]:
    if not intervals:
        return None
    med = median(intervals)
    # Weekly: ~7 days
    if 5 <= med <= 9:
        return "weekly"
    # Monthly: ~30 days
    if 26 <= med <= 35:
        return "monthly"
    # Yearly: ~365 days (optional)
    if 330 <= med <= 400:
        return "yearly"
    return None


def _cadence_consistency(cadence: str, intervals: List[int]) -> float:
    """Return fraction of intervals that fall within a tight window for cadence."""
    if not intervals:
        return 0.0
    if cadence == "weekly":
        lo, hi = 6, 9  # allow small jitter
    elif cadence == "monthly":
        lo, hi = 27, 33
    elif cadence == "yearly":
        lo, hi = 330, 400
    else:
        return 0.0
    good = sum(1 for d in intervals if lo <= d <= hi)
    return good / len(intervals)


def _status_for(cadence: str, last_seen: date, ref: Optional[date] = None) -> str:
    today = ref or date.today()
    days = (today - last_seen).days
    if cadence == "weekly":
        return "active" if days <= 14 else "paused"
    if cadence == "monthly":
        return "active" if days <= 45 else "paused"
    if cadence == "yearly":
        return "active" if days <= 450 else "paused"
    return "active"


def detect_subscriptions_for_user(conn: sqlite3.Connection, user_id: str) -> List[SubscriptionCandidate]:
    rows = conn.execute(
        """
        SELECT date, amount, COALESCE(merchant,'') AS merchant
        FROM transactions
        WHERE user_id = ? AND amount < 0
        ORDER BY date ASC
        """,
        (user_id,),
    ).fetchall()

    # Group by normalized merchant
    groups: dict[str, List[tuple[date, float]]] = {}
    for r in rows:
        m = (r["merchant"] or "").strip().lower()
        if not m:
            # skip unknown merchant
            continue
        try:
            d = _parse_date(r["date"])
        except Exception:
            continue
        amt = float(r["amount"])  # negative expense
        groups.setdefault(m, []).append((d, amt))

    candidates: List[SubscriptionCandidate] = []
    for m, items in groups.items():
        if len(items) < 3:
            continue
        items.sort(key=lambda x: x[0])
        dates = [d for d, _ in items]
        amts = [a for _, a in items]
        intervals = _intervals_in_days(dates)
        cad = _detect_cadence(intervals)

        if cad is None:
            # Heuristic fallback: if 3+ charges occur on near same day-of-month
            doms = [d.day for d in dates]
            spread = max(doms) - min(doms)
            if spread <= 3 and len(items) >= 3:
                cad = "monthly"
            else:
                continue

        # Timing consistency: require majority of intervals near cadence window
        cfrac = _cadence_consistency(cad, intervals)
        # Require at least 70% of intervals inside window
        if len(intervals) >= 2 and cfrac < 0.7:
            continue

        # Amount consistency: require majority of charges near the median
        med_abs, last_abs = _amounts_stats(amts)
        if med_abs == 0:
            continue
        tol = max(2.0, 0.10 * med_abs)  # tighter: 10% or $2
        within = [abs(abs(a) - med_abs) <= tol for a in amts]
        if len(within) >= 3:
            frac_within = sum(within) / len(within)
            if frac_within < 0.7:
                # Too much variability in amounts
                continue

        pchg = _price_change_pct(med_abs, last_abs)
        last_seen = dates[-1]
        status = _status_for(cad, last_seen)
        # Heuristic: detect possible free-trial conversion.
        # If the first charge is much smaller than the median (or near zero)
        # and the interval to the next charge is longer than ~14 days, mark trial_converted.
        trial = False
        try:
            first_abs = abs(amts[0])
            if len(intervals) >= 1 and intervals[0] >= 14:
                # If first charge was small relative to typical amount
                if first_abs <= 0.5 * med_abs or med_abs >= 3 * first_abs:
                    trial = True
        except Exception:
            trial = False
        candidates.append(
            SubscriptionCandidate(
                merchant=m,
                cadence=cad,
                avg_amount=round(med_abs, 2),
                last_seen=last_seen.isoformat(),
                price_change_pct=pchg,
                trial_converted=trial,
                status=status,
            )
        )

    return candidates


def sub_id(user_id: str, merchant: str) -> str:
    key = f"{user_id}|{merchant}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def upsert_subscriptions(conn: sqlite3.Connection, user_id: str, subs: List[SubscriptionCandidate]) -> Tuple[int, int]:
    inserted = 0
    updated = 0
    for s in subs:
        sid = sub_id(user_id, s.merchant)
        row = conn.execute(
            "SELECT id FROM subscriptions WHERE id = ?", (sid,)
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE subscriptions
                SET avg_amount = ?, cadence = ?, last_seen = ?, status = ?, price_change_pct = ?
                WHERE id = ?
                """,
                (s.avg_amount, s.cadence, s.last_seen,
                 s.status, s.price_change_pct, sid),
            )
            updated += 1
        else:
            conn.execute(
                """
                INSERT INTO subscriptions (id, user_id, merchant, avg_amount, cadence, last_seen, status, price_change_pct, trial_converted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sid, user_id, s.merchant, s.avg_amount, s.cadence, s.last_seen,
                 s.status, s.price_change_pct, int(bool(s.trial_converted))),
            )
            inserted += 1
    return inserted, updated
