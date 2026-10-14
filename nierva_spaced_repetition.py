"""Stateless, isolated spaced-repetition helpers.

These functions only model the timing and memory-state transitions for a single
review item and do not depend on any app-global state.
"""

from __future__ import annotations


def map_performance_to_rating(won: bool, time_taken: float, target_seconds: float) -> int:
    """Translate automated mini-game performance into Anki-style rating values."""
    if not won:
        return 1
    if time_taken <= (target_seconds * 0.5):
        return 4
    if time_taken <= target_seconds:
        return 3
    return 2


def advance_item_state(item_state: dict | None, rating: int) -> dict:
    """Return the next item state for a stateless SM-2-inspired memory engine."""
    state = dict(item_state or {
        "state": "LEARNING",
        "step_index": 0,
        "interval": 0,
        "ease_factor": 2.5,
    })
    current_state = state.get("state", "LEARNING")
    step_index = int(state.get("step_index", 0))
    interval = int(state.get("interval", 0))
    ease_factor = float(state.get("ease_factor", 2.5))

    if rating == 1:
        return {
            "state": "LEARNING",
            "step_index": 0,
            "interval": 0,
            "ease_factor": max(1.3, ease_factor),
        }

    if rating == 2:
        if current_state == "LEARNING":
            return {
                "state": "LEARNING",
                "step_index": max(0, step_index),
                "interval": max(1, interval),
                "ease_factor": max(1.3, ease_factor - 0.15),
            }
        return {
            "state": "REVIEW",
            "step_index": max(0, step_index),
            "interval": max(1, round(interval * 1.2)),
            "ease_factor": max(1.3, ease_factor - 0.15),
        }

    if rating == 3:
        if current_state == "LEARNING":
            next_step = step_index + 1
            next_state = "REVIEW" if next_step >= 2 else "LEARNING"
            next_interval = 1 if next_step >= 2 else interval
            return {
                "state": next_state,
                "step_index": next_step,
                "interval": next_interval,
                "ease_factor": max(1.3, ease_factor),
            }
        next_interval = max(1, round(interval * ease_factor))
        return {
            "state": "REVIEW",
            "step_index": step_index,
            "interval": next_interval,
            "ease_factor": max(1.3, ease_factor),
        }

    return {
        "state": "REVIEW",
        "step_index": step_index,
        "interval": 4,
        "ease_factor": min(3.0, ease_factor + 0.15),
    }
