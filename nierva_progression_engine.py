"""Compatibility imports for the progression domain model."""

from models.progression import (
    FIRST_RANK_XP_REQUIREMENT,
    RANK_XP_INCREMENT,
    apply_points_to_profile,
    get_rank_thresholds,
    profile_from_total_xp,
)

__all__ = [
    "FIRST_RANK_XP_REQUIREMENT",
    "RANK_XP_INCREMENT",
    "apply_points_to_profile",
    "get_rank_thresholds",
    "profile_from_total_xp",
]
