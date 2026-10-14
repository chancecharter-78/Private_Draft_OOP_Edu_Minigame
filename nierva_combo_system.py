"""Compatibility imports for combo controller and scoring model functions."""

from controllers.combo_controller import (
    apply_hard_fail,
    apply_soft_fail,
    apply_win,
    ensure_combo_state,
    render_combo_status,
)
from models.scoring import (
    calculate_combo_multiplier,
    compute_game_base_score,
    streak_for_multiplier,
)

__all__ = [
    "apply_hard_fail",
    "apply_soft_fail",
    "apply_win",
    "calculate_combo_multiplier",
    "compute_game_base_score",
    "ensure_combo_state",
    "render_combo_status",
    "streak_for_multiplier",
]
