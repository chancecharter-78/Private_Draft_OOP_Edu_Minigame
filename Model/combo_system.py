
from __future__ import annotations

try:
    from Model import logic_rules
except Exception:  # engine unavailable: use the Python rules below
    logic_rules = None


TIER_MULTIPLIERS = {
    (0, 2): 1.00,
    (3, 5): 1.05,
    (6, 8): 1.15,
    (9, 11): 1.25,
    (12, None): 1.35,
}


def calculate_combo_multiplier(streak: int) -> float:
    if logic_rules is not None:
        try:
            return logic_rules.combo_multiplier(streak)
        except logic_rules.LogicEngineError:
            pass
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
    if logic_rules is not None:
        try:
            return logic_rules.streak_for_multiplier(multiplier)
        except logic_rules.LogicEngineError:
            pass
    if multiplier >= 1.35:
        return 12
    if multiplier >= 1.25:
        return 9
    if multiplier >= 1.15:
        return 6
    if multiplier >= 1.05:
        return 3
    return 2


def win_state(current_streak: int) -> tuple[int, float]:
    streak = int(current_streak) + 1
    return streak, calculate_combo_multiplier(streak)


def soft_fail_state(current_streak: int) -> tuple[int, float]:
    current_multiplier = calculate_combo_multiplier(int(current_streak))
    next_multiplier = max(1.00, round(current_multiplier - 0.10, 2))
    return streak_for_multiplier(next_multiplier), next_multiplier


def hard_fail_state() -> tuple[int, float]:
    return 0, 1.00


def compute_game_base_score(
    game_name: str,
    *,
    elapsed_seconds: float,
    revealed_count: int | None = None,
    total_letters: int | None = None,
    correct_questions: int | None = None,
) -> int:
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
