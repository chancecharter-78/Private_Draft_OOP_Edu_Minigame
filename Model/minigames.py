"""Object-oriented wrappers around the existing minigame functions.

Minigame is an abstract base class. Slider, BitFit and Hacking inherit
from it and implement its abstract methods by calling the module-level
functions in slider.py, bit_fit.py and hacking.py. No Streamlit and no
SQL are used here (Model layer rules).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from Model import (
    bit_fit,
    combo_system,
    game_flow,
    hacking,
    slider,
    spaced_repetition,
)


class Minigame(ABC):
    """Shared behaviour for every minigame (abstract base class)."""

    def __init__(self, name: str):
        if name not in game_flow.GAME_ORDER:
            raise ValueError(f"Unknown minigame: {name!r}")
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def target_seconds(self) -> float:
        return game_flow.QUESTION_TARGET_SECONDS[self._name]

    @property
    def clear_range(self) -> tuple[int, int]:
        return game_flow.GAME_CLEAR_RANGES[self._name]

    def rate(self, won: bool, time_taken: float) -> int:
        """Automatic 1-4 rating using this game's target time."""
        return spaced_repetition.map_performance_to_rating(
            won, time_taken, self.target_seconds
        )

    @abstractmethod
    def start_round(self, question: dict, round_number: int = 1):
        """Build the game-specific data for one question."""

    @abstractmethod
    def base_score(self, elapsed_seconds: float, **progress) -> int:
        """Base points before the combo multiplier is applied."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self._name!r})"


class Slider(Minigame):
    def __init__(self):
        super().__init__("Slider")

    def start_round(self, question, round_number=1):
        return slider.shuffle_choices(question)

    def base_score(self, elapsed_seconds, **progress):
        return combo_system.compute_game_base_score(
            self.name,
            elapsed_seconds=elapsed_seconds,
            correct_questions=progress.get("correct_questions"),
        )


class BitFit(Minigame):
    def __init__(self):
        super().__init__("Bit Fit")

    def start_round(self, question, round_number=1):
        return bit_fit.create_cipher(
            question["correct_answer"], round_number
        )

    def base_score(self, elapsed_seconds, **progress):
        return combo_system.compute_game_base_score(
            self.name,
            elapsed_seconds=elapsed_seconds,
            revealed_count=progress.get("revealed_count"),
            total_letters=progress.get("total_letters"),
        )


class Hacking(Minigame):
    def __init__(self):
        super().__init__("Hacking")

    def start_round(self, question, round_number=1):
        words = [question["correct_answer"], *question["wrong_answers"]]
        return hacking.generate_terminal_dump_data(words)

    def base_score(self, elapsed_seconds, **progress):
        return combo_system.compute_game_base_score(
            self.name, elapsed_seconds=elapsed_seconds
        )


MINIGAMES = {game.name: game for game in (Slider(), BitFit(), Hacking())}


def get_minigame(name: str) -> Minigame:
    """Look up the shared minigame object by its display name."""
    return MINIGAMES[name]
