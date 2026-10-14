"""Combo-multiplier helpers for the flashcard minigames.

This module intentionally keeps all state transitions in plain dictionaries so it
can be used from Streamlit without hidden global state dependencies.
"""

from __future__ import annotations

import streamlit as st


TIER_MULTIPLIERS = {
    (0, 2): 1.00,
    (3, 5): 1.05,
    (6, 8): 1.15,
    (9, 11): 1.25,
    (12, None): 1.35,
}


def ensure_combo_state():
    """Create a small combo state store inside Streamlit session state."""
    st.session_state.setdefault("combo_streak", 0)
    st.session_state.setdefault("combo_multiplier", 1.00)
    return {
        "streak": st.session_state.combo_streak,
        "multiplier": st.session_state.combo_multiplier,
    }


def calculate_combo_multiplier(streak: int) -> float:
    """Return the active multiplier for a given consecutive-win streak."""
    if streak >= 12:
        return 1.35
    if streak >= 9:
        return 1.25
    if streak >= 6:
        return 1.15
    if streak >= 3:
        return 1.05
    return 1.00


def streak_for_multiplier(multiplier: float) -> int:
    """Match a multiplier back to the closest tier's representative streak."""
    if multiplier >= 1.35:
        return 12
    if multiplier >= 1.25:
        return 9
    if multiplier >= 1.15:
        return 6
    if multiplier >= 1.05:
        return 3
    return 2


def apply_win(game_name: str, *, elapsed_seconds: float, revealed_count: int | None = None,
             total_letters: int | None = None, correct_questions: int | None = None):
    """Advance the combo and return the final-per-round reward payload."""
    combo = ensure_combo_state()
    streak = int(combo["streak"]) + 1
    multiplier = calculate_combo_multiplier(streak)

    base_points = compute_game_base_score(
        game_name,
        elapsed_seconds=elapsed_seconds,
        revealed_count=revealed_count,
        total_letters=total_letters,
        correct_questions=correct_questions,
    )
    final_points = int(base_points * multiplier)

    st.session_state.combo_streak = streak
    st.session_state.combo_multiplier = multiplier
    st.toast(f"{game_name}: +{final_points} pts ({multiplier:.2f}x combo)")
    return {
        "game": game_name,
        "streak": streak,
        "multiplier": multiplier,
        "base_points": base_points,
        "final_points": final_points,
    }


def apply_soft_fail(game_name: str):
    """Decrease the multiplier by 0.10x without fully resetting the streak."""
    combo = ensure_combo_state()
    current_streak = int(combo["streak"])
    current_multiplier = calculate_combo_multiplier(current_streak)
    next_multiplier = max(1.00, round(current_multiplier - 0.10, 2))
    next_streak = streak_for_multiplier(next_multiplier)

    st.session_state.combo_streak = next_streak
    st.session_state.combo_multiplier = next_multiplier
    st.toast(f"{game_name}: combo slipped to {next_multiplier:.2f}x")
    return {
        "game": game_name,
        "streak": next_streak,
        "multiplier": next_multiplier,
    }


def apply_hard_fail(game_name: str):
    """Reset combo state completely for a timeout or no-answer failure."""
    st.session_state.combo_streak = 0
    st.session_state.combo_multiplier = 1.00
    st.toast(f"{game_name}: combo reset to 1.00x")
    return {
        "game": game_name,
        "streak": 0,
        "multiplier": 1.00,
    }


def compute_game_base_score(
    game_name: str,
    *,
    elapsed_seconds: float,
    revealed_count: int | None = None,
    total_letters: int | None = None,
    correct_questions: int | None = None,
) -> int:
    """Return the base award before the combo multiplier is applied."""
    game_name = (game_name or "").strip().lower()

    if game_name == "bit fit":
        reveal_count = int(revealed_count or 0)
        total_letters = int(total_letters or 0)
        if reveal_count < total_letters and elapsed_seconds < 10:
            return 500
        if reveal_count < total_letters and elapsed_seconds < 15:
            return 300
        if reveal_count <= 2 and elapsed_seconds < 20:
            return 200
        return 100

    if game_name == "hacking":
        if elapsed_seconds < 5:
            return 500
        if elapsed_seconds < 7:
            return 300
        if elapsed_seconds < 9:
            return 200
        return 100

    if game_name == "slider":
        correct_count = int(correct_questions or 0)
        if correct_count <= 4 and elapsed_seconds <= 5:
            return 500
        if correct_count <= 3 and elapsed_seconds <= 7:
            return 300
        if correct_count <= 4 and elapsed_seconds <= 11:
            return 200
        return 100

    return 100


def render_combo_status(label: str = "Combo", visible: bool = True):
    """Display the live multiplier and streak for the active game."""
    combo = ensure_combo_state()
    if visible:
        st.caption(f"{label}: {combo['multiplier']:.2f}x · streak {combo['streak']}")
    return combo
