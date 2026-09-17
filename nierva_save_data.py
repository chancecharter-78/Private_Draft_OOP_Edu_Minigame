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

    def get_summary(self) -> str:
        """Returns a formatted summary string of current save data."""
        return f"Player: {self.player_name} | Score: {self._score} | Level: {self._level} | Clears: {self._completed_rounds}"
