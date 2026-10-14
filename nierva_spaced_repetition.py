"""Anki-style rating and FSRS card scheduling helpers.

Rating conversion is stateless; persisted card scheduling is delegated to FSRS.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from fsrs import Card, Rating, Scheduler

def map_performance_to_rating(won: bool, time_taken: float, target_seconds: float) -> int:
    """Translate automated mini-game performance into Anki-style rating values."""
    if not won:
        return 1
    if target_seconds <= 0:
        raise ValueError("target_seconds must be greater than zero.")
    if time_taken <= (target_seconds * 0.5):
        return 4
    if time_taken <= target_seconds:
        return 3
    return 2


def combine_ratings(automated_rating: int, user_rating: int) -> int:
    """Apply the player's game-wide rating as a conservative ceiling."""
    if automated_rating not in (1, 2, 3, 4) or user_rating not in (1, 2, 3, 4):
        raise ValueError("ratings must be between 1 (Again) and 4 (Easy).")
    return min(automated_rating, user_rating)


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


def advance_review_card(card: dict | None, rating: int, reviewed_on: date | None = None) -> dict:
    """Use FSRS to schedule a card and return its JSON-serializable state."""
    try:
        fsrs_rating = Rating(rating)
    except ValueError as error:
        raise ValueError("rating must be between 1 (Again) and 4 (Easy).") from error

    review_datetime = None
    if reviewed_on is not None:
        review_datetime = datetime.combine(
            reviewed_on,
            time.min,
            tzinfo=timezone.utc,
        )

    if card:
        card_data = {
            key: value
            for key, value in card.items()
            if key in {
                "card_id",
                "state",
                "step",
                "stability",
                "difficulty",
                "due",
                "last_review",
            }
        }
        fsrs_card = Card.from_dict(card_data)
    elif review_datetime is not None:
        fsrs_card = Card(due=review_datetime)
    else:
        fsrs_card = Card()
    scheduler = Scheduler(enable_fuzzing=False)
    updated_card, _ = scheduler.review_card(
        fsrs_card,
        fsrs_rating,
        review_datetime=review_datetime,
    )
    updated_state = updated_card.to_dict()
    updated_state["last_rating"] = rating
    return updated_state
