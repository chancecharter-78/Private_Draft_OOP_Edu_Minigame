"""Stateless progression helpers for player rank and point thresholds."""

from __future__ import annotations


DEFAULT_THRESHOLD_CURVE = {
    1: 0,
    2: 250,
    3: 550,
    4: 900,
    5: 1350,
    6: 1900,
    7: 2600,
    8: 3400,
    9: 4300,
    10: 5300,
}


def get_rank_thresholds(current_rank: int, thresholds: dict[int, int] | None = None) -> int:
    """Return the points required for the given rank in a stateless way."""
    table = thresholds or DEFAULT_THRESHOLD_CURVE
    return table.get(current_rank, table[max(table)])


def apply_points_to_profile(
    profile: dict | None,
    points_earned: int,
    thresholds: dict[int, int] | None = None,
    blocker_ranks: set[int] | None = None,
) -> dict:
    """Apply points to a profile without mutating the input dictionary.

    The payload uses the three persistent variables required by the spec:
    {current_rank, current_points, is_locked}
    """
    state = dict(profile or {"current_rank": 1, "current_points": 0, "is_locked": False})
    current_rank = int(state.get("current_rank", 1))
    current_points = int(state.get("current_points", 0))
    is_locked = bool(state.get("is_locked", False))
    blockers = blocker_ranks or set()
    table = thresholds or DEFAULT_THRESHOLD_CURVE

    if is_locked:
        return {
            "current_rank": current_rank,
            "current_points": current_points + max(0, points_earned),
            "is_locked": True,
        }

    updated_points = current_points + max(0, points_earned)
    while updated_points >= get_rank_thresholds(current_rank, table):
        updated_points -= get_rank_thresholds(current_rank, table)
        current_rank += 1
        if current_rank in blockers:
            return {
                "current_rank": current_rank,
                "current_points": updated_points,
                "is_locked": True,
            }

    return {
        "current_rank": current_rank,
        "current_points": updated_points,
        "is_locked": False,
    }
