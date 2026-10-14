"""Streamlit state transitions for combo rewards and status."""

import streamlit as st

from models.scoring import (
    calculate_combo_multiplier,
    compute_game_base_score,
    streak_for_multiplier,
)


def ensure_combo_state():
    st.session_state.setdefault("combo_streak", 0)
    st.session_state.setdefault("combo_multiplier", 1.00)
    return {
        "streak": st.session_state.combo_streak,
        "multiplier": st.session_state.combo_multiplier,
    }


def apply_win(
    game_name: str,
    *,
    elapsed_seconds: float,
    revealed_count: int | None = None,
    total_letters: int | None = None,
    correct_questions: int | None = None,
):
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
    st.session_state.combo_streak = 0
    st.session_state.combo_multiplier = 1.00
    st.toast(f"{game_name}: combo reset to 1.00x")
    return {
        "game": game_name,
        "streak": 0,
        "multiplier": 1.00,
    }


def render_combo_status(label: str = "Combo", visible: bool = True):
    combo = ensure_combo_state()
    if visible:
        st.caption(f"{label}: {combo['multiplier']:.2f}x · streak {combo['streak']}")
    return combo
