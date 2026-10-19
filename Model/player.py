
from Model import progression_engine


class GameSaveData:
    def __init__(
        self,
        player_name="Player 1",
        starting_score=0,
        completed_rounds=0,
        history=None,
    ):
        self.player_name = player_name
        self._score = max(0, starting_score)
        self._completed_rounds = completed_rounds
        self._game_history = list(history or [])

    def check_score(self):
        return self._score

    def check_rank(self):
        return self.get_rank_progress()["rank"]

    def get_rank_progress(self):
        profile = progression_engine.profile_from_total_xp(self._score)
        rank = profile["current_rank"]
        return {
            "rank": rank,
            "current_xp": profile["current_points"],
            "required_xp": progression_engine.get_rank_thresholds(rank),
        }

    def check_completed_rounds(self):
        return self._completed_rounds

    def get_history(self):
        return list(self._game_history)

    def get_summary(self):
        return (
            f"Player: {self.player_name} | Score: {self._score} | "
            f"Rank: {self.check_rank()} | "
            f"Clears: {self._completed_rounds}"
        )


    def set_totals(self, score, completed_rounds=None):
        self._score = score
        if completed_rounds is not None:
            self._completed_rounds = completed_rounds

    def add_history_entry(self, game_name, level_cleared, points, details):
        self._game_history.append({
            "game": game_name,
            "level": level_cleared,
            "points": points,
            "details": details,
        })

    def clear_progress(self):
        self._score = 0
        self._completed_rounds = 0
        self._game_history.clear()
