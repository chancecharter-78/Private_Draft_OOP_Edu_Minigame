import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import nierva_app
import nierva_bit_fit
import nierva_combo_system
import nierva_hacking
import nierva_progression
import nierva_progression_engine
import nierva_save_data
import nierva_slider
import nierva_spaced_repetition
import nierva_timer
import psycopg
import streamlit as st
from controllers.application_controller import ApplicationController
from repositories import player_data_repository
from views import question_sets_view


VALID_CSV = """Game, Question ,Correct Answer,Wrong Answer 1,Wrong Answer 2,Wrong Answer 3,Difficulty
Science,Sample question?,MARS,VENUS,JUPITER,MERCURY,Easy
"""
SCIENCE_CSV_PATH = Path(__file__).with_name("test_data") / "science_question_set.csv"


class SQLitePostgresAdapter:
    def __init__(self, database_path):
        self.database_path = database_path
        self.connection = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.database_path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                username_key TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                password_salt TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                completed_rounds INTEGER NOT NULL DEFAULT 0,
                active_question_set INTEGER
            );
            CREATE TABLE IF NOT EXISTS question_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username_key TEXT NOT NULL REFERENCES players(username_key)
                    ON DELETE CASCADE,
                name TEXT NOT NULL COLLATE NOCASE,
                csv_text TEXT NOT NULL,
                UNIQUE (username_key, name)
            );
            CREATE TABLE IF NOT EXISTS player_clears (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username_key TEXT NOT NULL REFERENCES players(username_key)
                    ON DELETE CASCADE,
                game TEXT NOT NULL,
                level INTEGER NOT NULL,
                points INTEGER NOT NULL,
                details TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS question_review_cards (
                username_key TEXT NOT NULL REFERENCES players(username_key)
                    ON DELETE CASCADE,
                question_set_id INTEGER NOT NULL REFERENCES question_sets(id)
                    ON DELETE CASCADE,
                question_key TEXT NOT NULL,
                card_json TEXT NOT NULL,
                PRIMARY KEY (username_key, question_set_id, question_key)
            );
            """
        )
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.connection.close()

    def execute(self, statement, parameters=()):
        try:
            return self.connection.execute(statement.replace("%s", "?"), parameters)
        except sqlite3.IntegrityError as error:
            raise psycopg.errors.UniqueViolation(str(error)) from error


@contextmanager
def use_test_player_database(database_path):
    with (
        patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://test"}),
        patch.object(
            nierva_save_data.psycopg,
            "connect",
            side_effect=lambda *args, **kwargs: SQLitePostgresAdapter(database_path),
        ),
    ):
        yield


class QuestionDataTests(unittest.TestCase):
    def test_normalizes_headers_and_answers(self):
        questions = nierva_save_data.parse_question_csv(VALID_CSV)
        self.assertEqual(questions[0]["correct_answer"], "MARS")
        self.assertEqual(questions[0]["wrong_answers"], ("VENUS", "JUPITER", "MERCURY"))

    def test_rejects_duplicate_answers(self):
        csv_text = VALID_CSV.replace("VENUS", "mars")
        with self.assertRaisesRegex(ValueError, "all be different"):
            nierva_save_data.parse_question_csv(csv_text)

    def test_rejects_answers_over_limit_and_unsupported_characters(self):
        too_long = "A" * (nierva_save_data.MAX_ANSWER_LENGTH + 1)
        with self.assertRaisesRegex(ValueError, "longer than 32 characters"):
            nierva_save_data.parse_question_csv(VALID_CSV.replace("MARS", too_long))
        with self.assertRaisesRegex(ValueError, "spaces, and periods"):
            nierva_save_data.parse_question_csv(VALID_CSV.replace("MARS", "MARS!"))

    def test_accepts_answers_with_ten_letters(self):
        csv_text = VALID_CSV.replace("MARS", "ABCDEFGHIJ")
        questions = nierva_save_data.parse_question_csv(csv_text)
        self.assertEqual(questions[0]["correct_answer"], "ABCDEFGHIJ")

    def test_game_question_file_loads(self):
        self.assertTrue(nierva_save_data.parse_question_csv(
            nierva_save_data.QUESTION_DATABASE_PATH.read_text(encoding="utf-8-sig")
        ))

    def test_science_upload_csv_loads_for_all_game_answer_types(self):
        csv_text = SCIENCE_CSV_PATH.read_text(encoding="utf-8-sig")
        questions = nierva_save_data.parse_question_csv(csv_text)

        self.assertEqual(len(questions), 12)
        self.assertEqual(questions[2]["correct_answer"], "H2O")
        self.assertEqual(questions[5]["correct_answer"], "13.8")
        self.assertEqual(questions[9]["correct_answer"], "CARBON DIOXIDE")

        cipher = nierva_bit_fit.create_cipher("LAW OF SEGREGATION", 1)
        self.assertEqual(cipher["cipher_answer"], "LAWOFSEGREGATION")
        self.assertEqual(sum(cipher["active_columns"]), len("LAWOFSEGREGATION"))
        self.assertTrue(
            any(" " in answer for question in questions for answer in (
                question["correct_answer"],
                *question["wrong_answers"],
            ))
        )

    def test_bit_fit_defaults_to_ten_columns_and_expands_for_long_answers(self):
        short_answer = nierva_bit_fit.create_cipher("VERTEBRATE", 1)
        long_answer = nierva_bit_fit.create_cipher("VERTEBRATES", 1)

        self.assertEqual(short_answer["column_count"], 10)
        self.assertEqual(long_answer["column_count"], len("VERTEBRATES"))
        self.assertEqual(sum(long_answer["active_columns"]), len("VERTEBRATES"))

    def test_bit_fit_active_choices_match_required_character_type(self):
        cipher = nierva_bit_fit.create_cipher("A7.", 1)
        active_indexes = [
            index for index, active in enumerate(cipher["active_columns"]) if active
        ]

        for index, expected_character in zip(active_indexes, cipher["cipher_answer"]):
            choices = cipher["options"][index]
            self.assertIn(expected_character, choices)
            if expected_character.isalpha():
                self.assertTrue(all(choice.isalpha() for choice in choices))
            elif expected_character.isdigit():
                self.assertTrue(all(choice.isdigit() for choice in choices))
            else:
                self.assertTrue(all(not choice.isalnum() for choice in choices))

    def test_bit_fit_next_choice_follows_each_column_cycle_order(self):
        st.session_state.bf_options = [["V", "B", "C"]]
        st.session_state.bf_player = ["V"]

        self.assertEqual(nierva_bit_fit.get_next_choice(0), "B")

        st.session_state.bf_player[0] = "B"
        self.assertEqual(nierva_bit_fit.get_next_choice(0), "C")

        st.session_state.bf_player[0] = "C"
        self.assertEqual(nierva_bit_fit.get_next_choice(0), "V")

    def test_bit_fit_draws_all_cipher_columns_in_one_row(self):
        st.session_state.bf_reveal_started = 100.0
        st.session_state.bf_cols = 11
        st.session_state.bf_active = [True] * 11
        st.session_state.bf_answer_reveal_stages = [(0.0, 0.0, 0.0)] * 11
        st.session_state.bf_answer_letters = list("VERTEBRATES")
        st.session_state.bf_player = list("AAAAAAAAAAA")
        st.session_state.bf_options = [["A", "B", "C"] for _ in range(11)]
        st.session_state.bf_over = False
        columns = [unittest.mock.Mock() for _ in range(11)]

        with (
            patch.object(nierva_bit_fit.st, "columns", return_value=columns) as make_columns,
            patch.object(nierva_bit_fit.time, "monotonic", return_value=101.0),
        ):
            nierva_bit_fit.draw_cipher_columns()

        make_columns.assert_called_once_with(11)
        self.assertEqual(sum(column.button.call_count for column in columns), 11)
        self.assertEqual(sum(column.caption.call_count for column in columns), 11)


class ApplicationControllerTests(unittest.TestCase):
    def test_routes_game_and_info_pages_to_their_views(self):
        game_view = unittest.mock.Mock()
        info_view = unittest.mock.Mock()
        default_view = unittest.mock.Mock()
        controller = ApplicationController(
            {"Slider": game_view},
            {"Homepage": info_view},
            default_view,
        )

        controller.render_page("Slider")
        controller.render_page("Homepage")
        controller.render_page("Unknown")

        game_view.assert_called_once_with()
        info_view.assert_called_once_with()
        default_view.assert_called_once_with()


class QuestionSetWidgetTests(unittest.TestCase):
    def test_active_set_callback_ignores_missing_widget_state(self):
        with (
            patch.object(question_sets_view, "st") as streamlit,
            patch.object(question_sets_view, "set_active_question_set") as set_active,
        ):
            streamlit.session_state = {"username": "Owner"}

            question_sets_view.set_active_set()

        set_active.assert_not_called()

    def test_active_set_callback_rejects_non_id_values(self):
        with (
            patch.object(question_sets_view, "st") as streamlit,
            patch.object(question_sets_view, "set_active_question_set") as set_active,
        ):
            streamlit.session_state = {
                "username": "Owner",
                question_sets_view.ACTIVE_SET_STATE_KEY: "Science",
            }

            question_sets_view.set_active_set()

        streamlit.error.assert_called_once()
        set_active.assert_not_called()


class PlayerDataTests(unittest.TestCase):
    def test_missing_database_secret_reports_streamlit_setup(self):
        with (
            patch.dict(os.environ, {"SUPABASE_DB_URL": ""}),
            patch.object(nierva_save_data.st, "secrets", {}),
        ):
            with self.assertRaisesRegex(RuntimeError, "Settings → Secrets"):
                with nierva_save_data.open_player_database():
                    pass

    def test_uses_streamlit_secret_when_environment_variable_is_unset(self):
        with (
            patch.dict(os.environ, {"SUPABASE_DB_URL": ""}),
            patch.object(
                nierva_save_data.st,
                "secrets",
                {"SUPABASE_DB_URL": "postgresql://streamlit-secret"},
            ),
            patch.object(nierva_save_data.psycopg, "connect") as connect,
        ):
            connect.return_value.__enter__.return_value = object()

            with nierva_save_data.open_player_database():
                pass

        connect.assert_called_once_with(
            "postgresql://streamlit-secret",
            connect_timeout=10,
        )

    def test_username_uniqueness_password_and_saved_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "players.sqlite3"
            with use_test_player_database(database_path):
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
                self.assertEqual(saved_player.check_level(), 1)
                self.assertEqual(
                    saved_player.get_rank_progress(),
                    {"rank": 1, "current_xp": 300, "required_xp": 1500},
                )
                self.assertEqual(saved_player.check_completed_rounds(), 1)
                self.assertEqual(saved_player.get_history()[0]["points"], 300)
                self.assertEqual(nierva_save_data.get_leaderboard()[0]["Player"], "Test Player")

    def test_adventure_rank_uses_existing_lifetime_score_and_overflow(self):
        player = nierva_save_data.GameSaveData(starting_score=1500 + 1750 + 125)

        self.assertEqual(player.check_score(), 3375)
        self.assertEqual(player.check_level(), 3)
        self.assertEqual(
            player.get_rank_progress(),
            {"rank": 3, "current_xp": 125, "required_xp": 2000},
        )

    def test_question_sets_are_private_to_their_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "players.sqlite3"
            with use_test_player_database(database_path):
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

    def test_question_set_can_be_edited_only_by_its_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "players.sqlite3"
            with use_test_player_database(database_path):
                owner, _ = nierva_save_data.register_player("Owner", "owner password")
                other, _ = nierva_save_data.register_player("Other", "other password")
                set_id, message = nierva_save_data.save_question_set(
                    owner.player_name,
                    "Editable set",
                    VALID_CSV,
                )
                self.assertEqual(message, "")

                updated, message = nierva_save_data.update_question_set(
                    owner.player_name,
                    set_id,
                    "Edited set",
                    VALID_CSV.replace("Sample question?", "Edited question?"),
                )
                self.assertTrue(updated)
                self.assertEqual(message, "")
                self.assertEqual(
                    nierva_save_data.get_question_set_csv(owner.player_name, set_id),
                    VALID_CSV.replace("Sample question?", "Edited question?"),
                )
                saved_sets = nierva_save_data.list_question_sets(owner.player_name)
                self.assertEqual(len(saved_sets), 2)
                self.assertIn(
                    {"id": set_id, "name": "Edited set", "active": True},
                    saved_sets,
                )
                self.assertFalse(
                    nierva_save_data.update_question_set(
                        other.player_name,
                        set_id,
                        "Hijacked set",
                        VALID_CSV,
                    )[0]
                )

    def test_question_review_card_is_persisted_for_active_set(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "players.sqlite3"
            with use_test_player_database(database_path):
                player, _ = nierva_save_data.register_player(
                    "Review Player",
                    "review password",
                )

                card = player.record_question_review("Sample question?", 2)

                self.assertEqual(card["last_rating"], 2)
                self.assertEqual(
                    player.get_question_review_states()[
                        player._question_review_key("Sample question?")
                    ],
                    card,
                )

    def test_missing_question_review_schema_has_actionable_error(self):
        player = nierva_save_data.GameSaveData(player_name="Review Player")
        connection = unittest.mock.Mock()
        connection.execute.side_effect = psycopg.errors.UndefinedTable(
            "relation question_review_cards does not exist"
        )

        @contextmanager
        def missing_review_table():
            yield connection

        with patch.object(
            player_data_repository,
            "open_player_database",
            missing_review_table,
        ):
            for operation in (
                player.get_question_review_states,
                lambda: player.record_question_review("Sample question?", 2),
            ):
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(
                        nierva_save_data.QuestionReviewSchemaError,
                        "20261014000000_create_question_review_cards.sql",
                    ):
                        operation()


class GameRuleTests(unittest.TestCase):
    def test_missing_core_database_table_message_names_required_migrations(self):
        missing_table = psycopg.errors.UndefinedTable(
            'relation "question_sets" does not exist'
        )

        message = nierva_app.format_database_error(missing_table)
        self.assertIn("do not rerun the initial schema setup", message)
        self.assertIn("20261014000000_create_question_review_cards.sql", message)
        self.assertIn("SUPABASE_DB_URL", message)

    def test_slider_initialization_detects_missing_question_state(self):
        st.session_state.clear()
        st.session_state.update({
            key: None for key in nierva_slider.SLIDER_STATE_KEYS
        })
        st.session_state.pop("slider_question")

        self.assertFalse(nierva_slider.slider_state_initialized())

        st.session_state.slider_question = {"question": "Sample question?"}
        self.assertTrue(nierva_slider.slider_state_initialized())

    def test_slider_stop_ignores_duplicate_submission_in_one_round(self):
        st.session_state.clear()
        st.session_state.slider_over = False
        st.session_state.slider_round_locked = False
        st.session_state.slider_position_history = []
        st.session_state.slider_position = 50
        st.session_state.slider_correct_index = 2

        with patch.object(nierva_slider, "finish_round") as finish_round:
            nierva_slider.lock_slider()
            nierva_slider.lock_slider()

        finish_round.assert_called_once_with(True)
        self.assertTrue(st.session_state.slider_round_locked)

    def test_slider_position_uses_elapsed_time_not_frame_count(self):
        one_second = nierva_slider.advance_position(50, 1, 4, 1)
        five_refreshes = (50, 1)
        for _ in range(5):
            five_refreshes = nierva_slider.advance_position(
                *five_refreshes,
                4,
                0.2,
            )
        self.assertAlmostEqual(one_second[0], five_refreshes[0])
        self.assertEqual(one_second[1], five_refreshes[1])

    def test_slider_stop_uses_latest_recorded_tick(self):
        ticks = [(10, 1), (20, 1), (30, 1), (40, 1)]
        self.assertEqual(nierva_slider.get_stop_position(ticks), (40, 1))
        self.assertEqual(nierva_slider.get_stop_position(ticks[:2]), (20, 1))

    def test_slider_correct_zone_allows_one_tick_grace_on_both_sides(self):
        self.assertTrue(
            nierva_slider.is_position_within_correct_zone(48, 2, 3)
        )
        self.assertTrue(
            nierva_slider.is_position_within_correct_zone(77, 2, 3)
        )
        self.assertFalse(
            nierva_slider.is_position_within_correct_zone(46, 2, 3)
        )
        self.assertFalse(
            nierva_slider.is_position_within_correct_zone(78.1, 2, 3)
        )

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

    def test_homepage_navigation_clears_game_state(self):
        st.session_state.clear()
        st.session_state.page = "Slider"
        st.session_state.project = True
        st.session_state.game = True

        nierva_app.set_page("Homepage", True)

        self.assertEqual(st.session_state.page, "Homepage")
        self.assertFalse(st.session_state.project)
        self.assertFalse(st.session_state.game)

    def test_start_gate_uses_three_second_delay_then_three_second_countdown(self):
        self.assertEqual(nierva_progression.get_start_phase(0), ("delay", None))
        self.assertEqual(nierva_progression.get_start_phase(2.99), ("delay", None))
        self.assertEqual(nierva_progression.get_start_phase(3), ("countdown", 3))
        self.assertEqual(nierva_progression.get_start_phase(4), ("countdown", 2))
        self.assertEqual(nierva_progression.get_start_phase(5), ("countdown", 1))
        self.assertEqual(nierva_progression.get_start_phase(6), ("ready", None))

    def test_game_completion_waits_for_continue_before_switching(self):
        st.session_state.clear()
        nierva_progression.start_game("Bit Fit")
        st.session_state.flow_target = 1

        self.assertTrue(nierva_progression.record_success("Bit Fit", "Finished"))
        self.assertEqual(st.session_state.page, "Bit Fit")
        self.assertTrue(st.session_state.game_result_ready)
        self.assertEqual(st.session_state.game_result_message, "Finished")

    def test_question_review_ratings_never_exceed_user_rating(self):
        self.assertEqual(nierva_spaced_repetition.combine_ratings(1, 4), 1)
        self.assertEqual(nierva_spaced_repetition.combine_ratings(4, 3), 3)
        self.assertEqual(nierva_spaced_repetition.combine_ratings(2, 1), 1)

    def test_performance_rating_and_review_due_date(self):
        self.assertEqual(nierva_spaced_repetition.map_performance_to_rating(False, 1, 8), 1)
        self.assertEqual(nierva_spaced_repetition.map_performance_to_rating(True, 4, 8), 4)
        self.assertEqual(nierva_spaced_repetition.map_performance_to_rating(True, 8, 8), 3)
        self.assertEqual(nierva_spaced_repetition.map_performance_to_rating(True, 9, 8), 2)
        card = nierva_spaced_repetition.advance_review_card(
            None,
            3,
            reviewed_on=date(2026, 10, 14),
        )
        self.assertEqual(
            datetime.fromisoformat(card["last_review"]),
            datetime(2026, 10, 14, tzinfo=timezone.utc),
        )
        self.assertGreater(
            datetime.fromisoformat(card["due"]),
            datetime.fromisoformat(card["last_review"]),
        )


class ComboSystemTests(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()

    def test_combo_tiers_and_soft_fail_decay(self):
        self.assertAlmostEqual(nierva_combo_system.calculate_combo_multiplier(0), 1.00)
        self.assertAlmostEqual(nierva_combo_system.calculate_combo_multiplier(3), 1.05)
        self.assertAlmostEqual(nierva_combo_system.calculate_combo_multiplier(12), 1.35)

        st.session_state.combo_streak = 8
        st.session_state.combo_multiplier = 1.15
        result = nierva_combo_system.apply_soft_fail("Slider")
        self.assertEqual(result["streak"], 3)
        self.assertAlmostEqual(result["multiplier"], 1.05)

    def test_spaced_repetition_and_progression_are_stateless(self):
        item = {"state": "LEARNING", "step_index": 1, "interval": 1, "ease_factor": 2.5}
        next_item = nierva_spaced_repetition.advance_item_state(item, 3)
        self.assertEqual(next_item["state"], "REVIEW")
        self.assertEqual(next_item["interval"], 1)

        self.assertEqual(nierva_progression_engine.get_rank_thresholds(1), 1500)
        self.assertEqual(nierva_progression_engine.get_rank_thresholds(10), 3750)
        profile = {"current_rank": 1, "current_points": 1200, "is_locked": False}
        next_profile = nierva_progression_engine.apply_points_to_profile(profile, 500)
        self.assertEqual(next_profile["current_rank"], 2)
        self.assertEqual(next_profile["current_points"], 200)
        self.assertEqual(
            nierva_progression_engine.profile_from_total_xp(3250),
            {"current_rank": 3, "current_points": 0, "is_locked": False},
        )


if __name__ == "__main__":
    unittest.main()
