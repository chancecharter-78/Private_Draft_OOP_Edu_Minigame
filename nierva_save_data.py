import csv
import hashlib
import hashlib
import hmac
import json
import os
import random
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

import nierva_progression_engine
import nierva_spaced_repetition


QUESTION_DATABASE_PATH = Path(__file__).with_name("nierva_questions.csv")
REQUIRED_COLUMNS = (
    "game",
    "question",
    "correct answer",
    "wrong answer 1",
    "wrong answer 2",
    "wrong answer 3",
    "difficulty",
)
ANSWER_COLUMNS = (
    "correct answer",
    "wrong answer 1",
    "wrong answer 2",
    "wrong answer 3",
)
MAX_ANSWER_LENGTH = 32
PASSWORD_ITERATIONS = 310_000


class QuestionReviewSchemaError(RuntimeError):
    """Raised when the database is missing the question-review migration."""


QUESTION_REVIEW_MIGRATION_MESSAGE = (
    "Question review scheduling is not set up in the database. Run "
    "supabase/migrations/20261014000000_create_question_review_cards.sql "
    "in the Supabase SQL Editor, then retry."
)


def parse_question_csv(csv_text):
    try:
        rows = [row for row in csv.reader(StringIO(csv_text), strict=True) if row]
    except csv.Error as error:
        raise ValueError(f"Invalid CSV syntax: {error}") from error

    if len(rows) < 2:
        raise ValueError("Enter a CSV header and at least one data row.")

    headers = [header.strip().lower() for header in rows[0]]
    if any(not header for header in headers):
        raise ValueError("Column headers cannot be blank.")
    if len(headers) != len(set(headers)):
        raise ValueError("Column headers must be unique.")

    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}.")

    questions = []
    for line_number, values in enumerate(rows[1:], start=2):
        if len(values) != len(headers):
            raise ValueError(
                f"Row {line_number} has {len(values)} fields; expected {len(headers)}."
            )

        row = dict(zip(headers, (value.strip() for value in values)))
        if any(not row[column] for column in REQUIRED_COLUMNS):
            raise ValueError(f"Row {line_number} is missing a required value.")

        answers = [row[column].upper() for column in ANSWER_COLUMNS]
        if any(len(answer) > MAX_ANSWER_LENGTH for answer in answers):
            raise ValueError(
                f"Row {line_number} has an answer longer than "
                f"{MAX_ANSWER_LENGTH} characters."
            )
        if any(
            not answer.isascii()
            or any(not (character.isalnum() or character in " .") for character in answer)
            for answer in answers
        ):
            raise ValueError(
                f"Row {line_number} answers may contain only A-Z letters, "
                "0-9 numbers, spaces, and periods."
            )
        if len(set(answers)) != len(answers):
            raise ValueError(f"Row {line_number} answers must all be different.")

        questions.append({
            "game": row["game"],
            "question": row["question"],
            "correct_answer": answers[0],
            "wrong_answers": tuple(answers[1:]),
            "difficulty": row["difficulty"],
        })

    return questions


def validate_question_csv(csv_text):
    try:
        questions = parse_question_csv(csv_text)
    except ValueError as error:
        return False, str(error)
    return True, f"CSV is valid: {len(questions)} data row(s)."


@contextmanager
def open_player_database():
    database_url = os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        try:
            database_url = st.secrets.get("SUPABASE_DB_URL")
        except StreamlitSecretNotFoundError:
            database_url = None
    if not database_url:
        raise RuntimeError(
            "Supabase is not configured for this app. In Streamlit Community "
            "Cloud, open this app's Settings → Secrets and add "
            'SUPABASE_DB_URL = "postgresql://...". Copy the connection URI '
            "from your Supabase project's Connect settings. Do not share or "
            "commit the URI."
        )

    with psycopg.connect(database_url, connect_timeout=10) as connection:
        yield connection


def clean_username(username):
    name = username.strip()
    if not name:
        raise ValueError("Enter a username.")
    if len(name) > 20:
        raise ValueError("Usernames must be 20 characters or fewer.")
    if not all(char.isalnum() or char in " _-" for char in name):
        raise ValueError("Use only letters, numbers, spaces, hyphens, or underscores.")
    return name


def clean_password(password):
    if len(password) < 8:
        raise ValueError("Use a password with at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Passwords must be 128 characters or fewer.")
    return password


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )


def register_player(username, password):
    name = clean_username(username)
    password = clean_password(password)
    salt = secrets.token_bytes(16)
    password_hash = hash_password(password, salt)
    starter_csv = QUESTION_DATABASE_PATH.read_text(encoding="utf-8-sig")
    parse_question_csv(starter_csv)

    try:
        with open_player_database() as connection:
            connection.execute(
                """
                INSERT INTO players (username_key, username, password_salt, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (name.casefold(), name, salt.hex(), password_hash.hex()),
            )
            cursor = connection.execute(
                """
                INSERT INTO question_sets (username_key, name, csv_text)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (name.casefold(), "Starter questions", starter_csv),
            )
            set_id = cursor.fetchone()[0]
            connection.execute(
                "UPDATE players SET active_question_set = %s WHERE username_key = %s",
                (set_id, name.casefold()),
            )
    except psycopg.errors.UniqueViolation:
        return None, "Username already exists, please try another."

    return GameSaveData(player_name=name), ""


def authenticate_player(username, password):
    try:
        name = clean_username(username)
        password = clean_password(password)
    except ValueError:
        return None

    with open_player_database() as connection:
        row = connection.execute(
            """
            SELECT username, password_salt, password_hash, score, completed_rounds
            FROM players
            WHERE username_key = %s
            """,
            (name.casefold(),),
        ).fetchone()
        if row is None:
            return None

        saved_name, salt, saved_hash, score, completed_rounds = row
        if not salt or not saved_hash:
            return None
        entered_hash = hash_password(password, bytes.fromhex(salt)).hex()
        if not hmac.compare_digest(entered_hash, saved_hash):
            return None

        history = connection.execute(
            """
            SELECT game, level, points, details
            FROM player_clears
            WHERE username_key = %s
            ORDER BY id
            """,
            (name.casefold(),),
        ).fetchall()

    return GameSaveData(
        player_name=saved_name,
        starting_score=score,
        completed_rounds=completed_rounds,
        history=[
            {"game": game, "level": level, "points": points, "details": details}
            for game, level, points, details in history
        ],
    )


def list_question_sets(username):
    key = username.casefold()
    with open_player_database() as connection:
        rows = connection.execute(
            """
            SELECT question_sets.id, question_sets.name,
                question_sets.id = players.active_question_set
            FROM question_sets
            JOIN players USING (username_key)
            WHERE question_sets.username_key = %s
            ORDER BY lower(question_sets.name)
            """,
            (key,),
        ).fetchall()
    return [
        {"id": set_id, "name": name, "active": bool(active)}
        for set_id, name, active in rows
    ]


def get_question_set_csv(username, set_id=None):
    key = username.casefold()
    with open_player_database() as connection:
        if set_id is None:
            row = connection.execute(
                """
                SELECT csv_text
                FROM question_sets
                WHERE username_key = %s
                    AND id = (
                        SELECT active_question_set
                        FROM players
                        WHERE username_key = %s
                    )
                """,
                (key, key),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT csv_text FROM question_sets
                WHERE username_key = %s AND id = %s
                """,
                (key, set_id),
            ).fetchone()
    if row is None:
        raise ValueError("This question set is not available to this account.")
    return row[0]


def save_question_set(username, name, csv_text):
    set_name = name.strip()
    if not set_name:
        return None, "Enter a name for this question set."
    if len(set_name) > 60:
        return None, "Question set names must be 60 characters or fewer."
    if not all(char.isalnum() or char in " _-." for char in set_name):
        return None, "Use only letters, numbers, spaces, periods, hyphens, or underscores."
    parse_question_csv(csv_text)

    key = username.casefold()
    try:
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                INSERT INTO question_sets (username_key, name, csv_text)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (key, set_name, csv_text),
            )
            set_id = cursor.fetchone()[0]
            connection.execute(
                "UPDATE players SET active_question_set = %s WHERE username_key = %s",
                (set_id, key),
            )
    except psycopg.errors.UniqueViolation:
        return None, "A question set with that name already exists."
    return set_id, ""


def update_question_set(username, set_id, name, csv_text):
    set_name = name.strip()
    if not set_name:
        return False, "Enter a name for this question set."
    if len(set_name) > 60:
        return False, "Question set names must be 60 characters or fewer."
    if not all(char.isalnum() or char in " _-." for char in set_name):
        return False, "Use only letters, numbers, spaces, periods, hyphens, or underscores."
    parse_question_csv(csv_text)

    key = username.casefold()
    try:
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                UPDATE question_sets
                SET name = %s, csv_text = %s
                WHERE username_key = %s AND id = %s
                """,
                (set_name, csv_text, key, set_id),
            )
    except psycopg.errors.UniqueViolation:
        return False, "A question set with that name already exists."
    if cursor.rowcount != 1:
        return False, "This question set is not available to this account."
    return True, ""


def set_active_question_set(username, set_id):
    key = username.casefold()
    with open_player_database() as connection:
        cursor = connection.execute(
            """
            UPDATE players
            SET active_question_set = %s
            WHERE username_key = %s
                AND EXISTS (
                    SELECT 1 FROM question_sets
                    WHERE id = %s AND username_key = %s
                )
            """,
            (set_id, key, set_id, key),
        )
    return cursor.rowcount == 1


def delete_question_set(username, set_id):
    key = username.casefold()
    with open_player_database() as connection:
        cursor = connection.execute(
            """
            DELETE FROM question_sets
            WHERE id = %s AND username_key = %s
                AND id != (
                    SELECT active_question_set
                    FROM players
                    WHERE username_key = %s
                )
            """,
            (set_id, key, key),
        )
    return cursor.rowcount == 1


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

    def check_level(self):
        return self.get_rank_progress()["rank"]

    def get_rank_progress(self):
        profile = nierva_progression_engine.profile_from_total_xp(self._score)
        rank = profile["current_rank"]
        return {
            "rank": rank,
            "current_xp": profile["current_points"],
            "required_xp": nierva_progression_engine.get_rank_thresholds(rank),
        }

    def check_completed_rounds(self):
        return self._completed_rounds

    def add_score(self, amount):
        if amount <= 0:
            return False
        with open_player_database() as connection:
            cursor = connection.execute(
                "UPDATE players SET score = score + %s WHERE username_key = %s",
                (amount, self.player_name.casefold()),
            )
            if cursor.rowcount != 1:
                raise ValueError("This player is not in the shared leaderboard.")
            self._score = connection.execute(
                "SELECT score FROM players WHERE username_key = %s",
                (self.player_name.casefold(),),
            ).fetchone()[0]
        return True

    def record_clear(self, game_name, level_cleared, details="", points=None):
        if level_cleared <= 0:
            return False
        if points is None:
            points = 100 * level_cleared
        if points < 0:
            return False

        key = self.player_name.casefold()
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                UPDATE players
                SET score = score + %s, completed_rounds = completed_rounds + 1
                WHERE username_key = %s
                """,
                (points, key),
            )
            if cursor.rowcount != 1:
                raise ValueError("This player is not in the shared leaderboard.")
            connection.execute(
                """
                INSERT INTO player_clears (username_key, game, level, points, details)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (key, game_name, level_cleared, points, details),
            )
            score, completed_rounds = connection.execute(
                """
                SELECT score, completed_rounds
                FROM players
                WHERE username_key = %s
                """,
                (key,),
            ).fetchone()
        self._score = score
        self._score = score
        self._completed_rounds = completed_rounds
        self._game_history.append({
            "game": game_name,
            "level": level_cleared,
            "points": points,
            "details": details,
        })
        return True

    def reset_save(self):
        key = self.player_name.casefold()
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                UPDATE players
                SET score = 0, level = 1, completed_rounds = 0
                WHERE username_key = %s
                """,
                (key,),
            )
            if cursor.rowcount != 1:
                raise ValueError("This player is not in the shared leaderboard.")
            connection.execute(
                "DELETE FROM player_clears WHERE username_key = %s",
                (key,),
            )
        self._score = 0
        self._completed_rounds = 0
        self._game_history.clear()
        return True

    def get_history(self):
        return list(self._game_history)

    def get_random_question(self, previous_question=None):
        csv_text = get_question_set_csv(self.player_name)
        questions = parse_question_csv(csv_text)
        if previous_question is None:
            previous_questions = set()
        elif isinstance(previous_question, str):
            previous_questions = {previous_question}
        else:
            previous_questions = set(previous_question)
        available = [
            question for question in questions
            if question["question"] not in previous_questions
        ]
        candidates = available or questions
        review_states = self.get_question_review_states()
        now = datetime.now(timezone.utc)
        scheduled_candidates = [
            (
                question,
                self._get_card_due(
                    review_states.get(
                        self._question_review_key(question["question"]),
                    ),
                    now,
                ),
            )
            for question in candidates
        ]
        due_candidates = [
            question for question, due in scheduled_candidates if due <= now
        ]
        if due_candidates:
            return random.choice(due_candidates)

        if scheduled_candidates:
            earliest_due = min(due for _, due in scheduled_candidates)
            earliest_candidates = [
                question for question, due in scheduled_candidates
                if due == earliest_due
            ]
            return random.choice(earliest_candidates)
        return random.choice(candidates)

    @staticmethod
    def _question_review_key(question_text):
        return hashlib.sha256(question_text.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_card_due(card, default_due):
        if not card or not card.get("due"):
            return default_due
        due = datetime.fromisoformat(card["due"])
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return due.astimezone(timezone.utc)

    def _active_question_set_id(self, connection):
        row = connection.execute(
            "SELECT active_question_set FROM players WHERE username_key = %s",
            (self.player_name.casefold(),),
        ).fetchone()
        if row is None or row[0] is None:
            raise ValueError("This player does not have an active question set.")
        return row[0]

    def get_question_review_states(self):
        key = self.player_name.casefold()
        try:
            with open_player_database() as connection:
                set_id = self._active_question_set_id(connection)
                rows = connection.execute(
                    """
                    SELECT question_key, card_json
                    FROM question_review_cards
                    WHERE username_key = %s AND question_set_id = %s
                    """,
                    (key, set_id),
                ).fetchall()
        except (
            psycopg.errors.UndefinedTable,
            psycopg.errors.UndefinedColumn,
        ) as error:
            raise QuestionReviewSchemaError(
                QUESTION_REVIEW_MIGRATION_MESSAGE
            ) from error
        return {
            question_key: json.loads(card_json)
            for question_key, card_json in rows
        }

    def record_question_review(self, question_text, rating):
        key = self.player_name.casefold()
        question_key = self._question_review_key(question_text)
        try:
            with open_player_database() as connection:
                set_id = self._active_question_set_id(connection)
                row = connection.execute(
                    """
                    SELECT card_json FROM question_review_cards
                    WHERE username_key = %s AND question_set_id = %s
                        AND question_key = %s
                    """,
                    (key, set_id, question_key),
                ).fetchone()
                current_card = json.loads(row[0]) if row else None
                next_card = nierva_spaced_repetition.advance_review_card(
                    current_card,
                    rating,
                )
                connection.execute(
                    """
                    INSERT INTO question_review_cards
                        (username_key, question_set_id, question_key, card_json)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username_key, question_set_id, question_key)
                    DO UPDATE SET card_json = excluded.card_json
                    """,
                    (key, set_id, question_key, json.dumps(next_card)),
                )
        except (
            psycopg.errors.UndefinedTable,
            psycopg.errors.UndefinedColumn,
        ) as error:
            raise QuestionReviewSchemaError(
                QUESTION_REVIEW_MIGRATION_MESSAGE
            ) from error
        return next_card

    def get_summary(self):
        return (
            f"Player: {self.player_name} | Score: {self._score} | "
            f"Adventure Rank: {self.check_level()} | "
            f"Clears: {self._completed_rounds}"
        )


def get_leaderboard(limit=20):
    with open_player_database() as connection:
        rows = connection.execute(
            """
            SELECT username, score, completed_rounds
            FROM players
            ORDER BY score DESC, completed_rounds DESC, lower(username)
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [
        {"Player": name, "Score": score, "Clears": clears}
        for name, score, clears in rows
    ]


def ensure_current_save_data(save_data=None):
    if save_data is None:
        return GameSaveData()
    if callable(getattr(save_data, "get_random_question", None)):
        return save_data

    return GameSaveData(
        player_name=getattr(save_data, "player_name", "Player 1"),
        starting_score=getattr(save_data, "_score", 0),
        completed_rounds=getattr(save_data, "_completed_rounds", 0),
        history=getattr(save_data, "_game_history", []),
    )
