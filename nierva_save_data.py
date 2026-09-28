import csv
import random
from pathlib import Path

QUESTION_DATABASE_PATH = Path(__file__).with_name("nierva_questions.csv")


def ensure_current_save_data(save_data=None):
    if save_data is None:
        return GameSaveData()
    if callable(getattr(save_data, "get_random_question", None)):
        return save_data

    upgraded = GameSaveData(
        player_name=getattr(save_data, "player_name", "Player 1"),
        starting_score=getattr(save_data, "_score", 0),
    )
    upgraded._level = getattr(save_data, "_level", 1)
    upgraded._completed_rounds = getattr(save_data, "_completed_rounds", 0)
    upgraded._game_history = list(getattr(save_data, "_game_history", []))
    return upgraded


class GameSaveData:
    def __init__(self, player_name="Player 1", starting_score=0):
        self.player_name = player_name
        self._score = starting_score  # Encapsulated state variable
        self._level = 1
        self._completed_rounds = 0
        self._game_history = []

    def check_score(self) -> int:
        """Returns the current accumulated score (Encapsulated reader)."""
        return self._score

    def check_level(self) -> int:
        """Returns current player level."""
        return self._level

    def check_completed_rounds(self) -> int:
        """Returns total cleared minigame rounds."""
        return self._completed_rounds

    def add_score(self, amount: int) -> bool:
        """Increases player score if amount is valid and positive."""
        if amount > 0:
            self._score += amount
            return True
        return False

    def record_clear(self, game_name: str, level_cleared: int, details: str = "") -> bool:
        """Records a successful minigame level clear and updates save progress."""
        if level_cleared > 0:
            points = 100 * level_cleared
            self.add_score(points)
            self._completed_rounds += 1
            self._level += 1
            self._game_history.append({
                "game": game_name,
                "level": level_cleared,
                "points": points,
                "details": details
            })
            return True
        return False

    def reset_save(self) -> bool:
        """Resets save data back to initial Set 1 state."""
        self._score = 0
        self._level = 1
        self._completed_rounds = 0
        self._game_history.clear()
        return True

    def get_history(self) -> list:
        """Returns copy of game clear history logs."""
        return list(self._game_history)

    def get_random_question(self, previous_question: str | None = None) -> dict:
        """Loads a random question from the CSV database."""
        with QUESTION_DATABASE_PATH.open(encoding="utf-8-sig", newline="") as question_file:
            reader = csv.DictReader(question_file)
            questions = []
            for row_number, row in enumerate(reader, start=2):
                required_values = (
                    row.get("game"),
                    row.get("question"),
                    row.get("correct answer"),
                    row.get("wrong answer 1"),
                    row.get("wrong answer 2"),
                    row.get("wrong answer 3"),
                    row.get("difficulty"),
                )
                if any(value is None or not value.strip() for value in required_values):
                    raise ValueError(f"Question CSV row {row_number} has a missing required value.")

                questions.append({
                    "game": row["game"].strip(),
                    "question": row["question"].strip(),
                    "correct_answer": row["correct answer"].strip().upper(),
                    "wrong_answers": (
                        row["wrong answer 1"].strip().upper(),
                        row["wrong answer 2"].strip().upper(),
                        row["wrong answer 3"].strip().upper(),
                    ),
                    "difficulty": row["difficulty"].strip(),
                })

        if not questions:
            raise ValueError("The question CSV does not contain any question rows.")

        available_questions = [
            question for question in questions
            if question["question"] != previous_question
        ] or questions
        return random.choice(available_questions)

    def get_summary(self) -> str:
        """Returns a formatted summary string of current save data."""
        return f"Player: {self.player_name} | Score: {self._score} | Level: {self._level} | Clears: {self._completed_rounds}"
