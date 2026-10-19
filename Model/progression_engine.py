
from __future__ import annotations


FIRST_RANK_XP_REQUIREMENT = 1500
RANK_XP_INCREMENT = 250


def get_rank_thresholds(current_rank: int, thresholds: dict[int, int] | None = None) -> int:
    if current_rank < 1:
        current_rank = 1
    if thresholds:
        return thresholds.get(current_rank, thresholds[max(thresholds)])
    return FIRST_RANK_XP_REQUIREMENT + RANK_XP_INCREMENT * (current_rank - 1)


def profile_from_total_xp(total_xp: int) -> dict[str, int | bool]:
    remaining_xp = max(0, int(total_xp))
    current_rank = 1
    while remaining_xp >= get_rank_thresholds(current_rank):
        remaining_xp -= get_rank_thresholds(current_rank)
        current_rank += 1

    return {
        "current_rank": current_rank,
        "current_points": remaining_xp,
        "is_locked": False,
    }


def apply_points_to_profile(
    profile: dict | None,
    points_earned: int,
    thresholds: dict[int, int] | None = None,
    blocker_ranks: set[int] | None = None,
) -> dict:
    state = dict(profile or {"current_rank": 1, "current_points": 0, "is_locked": False})
    current_rank = int(state.get("current_rank", 1))
    current_points = int(state.get("current_points", 0))
    is_locked = bool(state.get("is_locked", False))
    blockers = blocker_ranks or set()
    table = thresholds

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
