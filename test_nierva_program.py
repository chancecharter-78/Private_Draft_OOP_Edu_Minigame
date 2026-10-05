import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nierva_bit_fit
import nierva_hacking
import nierva_save_data
import nierva_slider
import nierva_timer


VALID_CSV = """Game, Question ,Correct Answer,Wrong Answer 1,Wrong Answer 2,Wrong Answer 3,Difficulty
Science,Sample question?,MARS,VENUS,JUPITER,MERCURY,Easy
"""


class QuestionDataTests(unittest.TestCase):
    def test_normalizes_headers_and_answers(self):
        questions = nierva_save_data.parse_question_csv(VALID_CSV)
        self.assertEqual(questions[0]["correct_answer"], "MARS")
        self.assertEqual(questions[0]["wrong_answers"], ("VENUS", "JUPITER", "MERCURY"))

    def test_rejects_duplicate_answers(self):
        csv_text = VALID_CSV.replace("VENUS", "mars")
        with self.assertRaisesRegex(ValueError, "all be different"):
            nierva_save_data.parse_question_csv(csv_text)

    def test_rejects_long_and_non_letter_answers(self):
        with self.assertRaisesRegex(ValueError, "longer than 10"):
            nierva_save_data.parse_question_csv(VALID_CSV.replace("MARS", "SUPERCALIFRAG"))
        with self.assertRaisesRegex(ValueError, "only A-Z"):
            nierva_save_data.parse_question_csv(VALID_CSV.replace("MARS", "M4RS"))

    def test_accepts_answers_with_ten_letters(self):
        csv_text = VALID_CSV.replace("MARS", "ABCDEFGHIJ")
        questions = nierva_save_data.parse_question_csv(csv_text)
        self.assertEqual(questions[0]["correct_answer"], "ABCDEFGHIJ")

    def test_game_question_file_loads(self):
        self.assertTrue(nierva_save_data.parse_question_csv(
            nierva_save_data.QUESTION_DATABASE_PATH.read_text(encoding="utf-8-sig")
        ))


class PlayerDataTests(unittest.TestCase):
    def test_username_uniqueness_password_and_saved_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "players.sqlite3"
            with patch.object(nierva_save_data, "PLAYER_DATABASE_PATH", database_path):
                player, message = nierva_save_data.register_player(
                    "Test Player",
                    "correct horse battery",
                )
                self.assertEqual(message, "")
                self.assertIsNotNone(player)
                self.assertTrue(player.record_clear("Bit Fit", 1, points=300))

                duplicate, message = nierva_save_data.register_player(
                    "test player",
                    "another password",
                )
                self.assertIsNone(duplicate)
                self.assertEqual(message, "Username already exists, please try another.")

                self.assertIsNone(
                    nierva_save_data.authenticate_player("Test Player", "wrong password")
                )
                saved_player = nierva_save_data.authenticate_player(
                    "TEST PLAYER",
                    "correct horse battery",
                )
                self.assertEqual(saved_player.check_score(), 300)
                self.assertEqual(saved_player.check_completed_rounds(), 1)
                self.assertEqual(saved_player.get_history()[0]["points"], 300)
                self.assertEqual(nierva_save_data.get_leaderboard()[0]["Player"], "Test Player")

    def test_question_sets_are_private_to_their_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "players.sqlite3"
            with patch.object(nierva_save_data, "PLAYER_DATABASE_PATH", database_path):
                owner, _ = nierva_save_data.register_player("Owner", "owner password")
                other, _ = nierva_save_data.register_player("Other", "other password")
                set_id, message = nierva_save_data.save_question_set(
                    owner.player_name,
                    "Copied set",
                    VALID_CSV,
                )

                self.assertEqual(message, "")
                self.assertFalse(
                    nierva_save_data.set_active_question_set(other.player_name, set_id)
                )
                self.assertEqual(
                    owner.get_random_question()["question"],
                    "Sample question?",
                )
                self.assertNotEqual(
                    nierva_save_data.get_question_set_csv(owner.player_name),
                    nierva_save_data.get_question_set_csv(other.player_name),
                )
                with self.assertRaisesRegex(ValueError, "not available"):
                    nierva_save_data.get_question_set_csv(other.player_name, set_id)


class GameRuleTests(unittest.TestCase):
    def test_slider_position_uses_elapsed_time_not_frame_count(self):
        one_second = nierva_slider.advance_position(50, 1, 4, 1)
        ten_frames = (50, 1)
        for _ in range(10):
            ten_frames = nierva_slider.advance_position(*ten_frames, 4, 0.1)
        self.assertAlmostEqual(one_second[0], ten_frames[0])
        self.assertEqual(one_second[1], ten_frames[1])

    def test_slider_stop_uses_two_recorded_ticks_earlier(self):
        ticks = [(10, 1), (20, 1), (30, 1), (40, 1)]
        self.assertEqual(nierva_slider.get_stop_position(ticks), (20, 1))
        self.assertEqual(nierva_slider.get_stop_position(ticks[:2]), (10, 1))

    def test_bit_fit_points_use_reveal_tiers(self):
        self.assertEqual(nierva_bit_fit.calculate_points(2, 0, 8), 600)
        self.assertEqual(nierva_bit_fit.calculate_points(2, 3, 8), 500)
        self.assertEqual(nierva_bit_fit.calculate_points(2, 4, 8), 200)
        self.assertEqual(nierva_bit_fit.calculate_points(2, 8, 8), 100)

    def test_hacking_feedback_counts_repeated_letters_once(self):
        self.assertEqual(nierva_hacking.evaluate_guess("LLLLE", "LEVEL"), "L#--#")

    def test_terminal_dump_expands_for_long_answers(self):
        word = "A" * 55
        dump = nierva_hacking.generate_terminal_dump([word])
        self.assertIn(word, dump)
        self.assertEqual(len(dump.splitlines()[0]), 55)

    def test_timer_rounds_to_nearest_tenth(self):
        self.assertEqual(nierva_timer.format_time(2.3), "00:02.3")
        self.assertEqual(nierva_timer.format_time(4.6), "00:04.6")


if __name__ == "__main__":
    unittest.main()
