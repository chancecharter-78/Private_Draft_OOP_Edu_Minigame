import csv
import hashlib
import hmac
import random
import secrets
import sqlite3
from contextlib import contextmanager
from io import StringIO
from pathlib import Path


QUESTION_DATABASE_PATH = Path(__file__).with_name("nierva_questions.csv")
PLAYER_DATABASE_PATH = Path(__file__).with_name("nierva_players.sqlite3")
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
MAX_ANSWER_LENGTH = 12
PASSWORD_ITERATIONS = 310_000


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
                f"Row {line_number} has an answer longer than {MAX_ANSWER_LENGTH} letters."
            )
        if any(not answer.isascii() or not answer.isalpha() for answer in answers):
            raise ValueError(f"Row {line_number} answers must contain only A-Z letters.")
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
    connection = sqlite3.connect(PLAYER_DATABASE_PATH, timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.execute(
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
            )
            """
        )

        player_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(players)")
        }
        for name, sql_type in (
            ("password_salt", "TEXT NOT NULL DEFAULT ''"),
            ("password_hash", "TEXT NOT NULL DEFAULT ''"),
            ("active_question_set", "INTEGER"),
        ):
            if name not in player_columns:
                connection.execute(f"ALTER TABLE players ADD COLUMN {name} {sql_type}")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS question_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username_key TEXT NOT NULL,
                name TEXT NOT NULL COLLATE NOCASE,
                csv_text TEXT NOT NULL,
                FOREIGN KEY (username_key) REFERENCES players(username_key)
                    ON DELETE CASCADE,
                UNIQUE (username_key, name)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_clears (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username_key TEXT NOT NULL,
                game TEXT NOT NULL,
                level INTEGER NOT NULL,
                points INTEGER NOT NULL,
                details TEXT NOT NULL,
                FOREIGN KEY (username_key) REFERENCES players(username_key)
                    ON DELETE CASCADE
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


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
                VALUES (?, ?, ?, ?)
                """,
                (name.casefold(), name, salt.hex(), password_hash.hex()),
            )
            cursor = connection.execute(
                """
                INSERT INTO question_sets (username_key, name, csv_text)
                VALUES (?, ?, ?)
                """,
                (name.casefold(), "Starter questions", starter_csv),
            )
            connection.execute(
                "UPDATE players SET active_question_set = ? WHERE username_key = ?",
                (cursor.lastrowid, name.casefold()),
            )
    except sqlite3.IntegrityError:
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
            SELECT username, password_salt, password_hash, score, level, completed_rounds
            FROM players
            WHERE username_key = ?
            """,
            (name.casefold(),),
        ).fetchone()
        if row is None:
            return None

        saved_name, salt, saved_hash, score, level, completed_rounds = row
        if not salt or not saved_hash:
            return None
        entered_hash = hash_password(password, bytes.fromhex(salt)).hex()
        if not hmac.compare_digest(entered_hash, saved_hash):
            return None

        history = connection.execute(
            """
            SELECT game, level, points, details
            FROM player_clears
            WHERE username_key = ?
            ORDER BY id
            """,
            (name.casefold(),),
        ).fetchall()

    return GameSaveData(
        player_name=saved_name,
        starting_score=score,
        level=level,
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
            WHERE question_sets.username_key = ?
            ORDER BY question_sets.name COLLATE NOCASE
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
                WHERE username_key = ?
                    AND id = (
                        SELECT active_question_set
                        FROM players
                        WHERE username_key = ?
                    )
                """,
                (key, key),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT csv_text FROM question_sets
                WHERE username_key = ? AND id = ?
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
                VALUES (?, ?, ?)
                """,
                (key, set_name, csv_text),
            )
            set_id = cursor.lastrowid
            connection.execute(
                "UPDATE players SET active_question_set = ? WHERE username_key = ?",
                (set_id, key),
            )
    except sqlite3.IntegrityError:
        return None, "A question set with that name already exists."
    return set_id, ""


def set_active_question_set(username, set_id):
    key = username.casefold()
    with open_player_database() as connection:
        cursor = connection.execute(
            """
            UPDATE players
            SET active_question_set = ?
            WHERE username_key = ?
                AND EXISTS (
                    SELECT 1 FROM question_sets
                    WHERE id = ? AND username_key = ?
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
            WHERE id = ? AND username_key = ?
                AND id != (
                    SELECT active_question_set
                    FROM players
                    WHERE username_key = ?
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
        level=1,
        completed_rounds=0,
        history=None,
    ):
        self.player_name = player_name
        self._score = starting_score
        self._level = level
        self._completed_rounds = completed_rounds
        self._game_history = list(history or [])

    def check_score(self):
        return self._score

    def check_level(self):
        return self._level

    def check_completed_rounds(self):
        return self._completed_rounds

    def add_score(self, amount):
        if amount <= 0:
            return False
        with open_player_database() as connection:
            cursor = connection.execute(
                "UPDATE players SET score = score + ? WHERE username_key = ?",
                (amount, self.player_name.casefold()),
            )
            if cursor.rowcount != 1:
                raise ValueError("This player is not in the local leaderboard.")
            self._score = connection.execute(
                "SELECT score FROM players WHERE username_key = ?",
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
                SET score = score + ?, level = level + 1,
                    completed_rounds = completed_rounds + 1
                WHERE username_key = ?
                """,
                (points, key),
            )
            if cursor.rowcount != 1:
                raise ValueError("This player is not in the local leaderboard.")
            connection.execute(
                """
                INSERT INTO player_clears (username_key, game, level, points, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key, game_name, level_cleared, points, details),
            )
            score, level, completed_rounds = connection.execute(
                """
                SELECT score, level, completed_rounds
                FROM players
                WHERE username_key = ?
                """,
                (key,),
            ).fetchone()

        self._score = score
        self._level = level
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
                WHERE username_key = ?
                """,
                (key,),
            )
            if cursor.rowcount != 1:
                raise ValueError("This player is not in the local leaderboard.")
            connection.execute(
                "DELETE FROM player_clears WHERE username_key = ?",
                (key,),
            )
        self._score = 0
        self._level = 1
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
        return random.choice(available or questions)

    def get_summary(self):
        return (
            f"Player: {self.player_name} | Score: {self._score} | "
            f"Level: {self._level} | Clears: {self._completed_rounds}"
        )


def get_leaderboard(limit=20):
    with open_player_database() as connection:
        rows = connection.execute(
            """
            SELECT username, score, completed_rounds
            FROM players
            ORDER BY score DESC, completed_rounds DESC, username COLLATE NOCASE
            LIMIT ?
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
        level=getattr(save_data, "_level", 1),
        completed_rounds=getattr(save_data, "_completed_rounds", 0),
        history=getattr(save_data, "_game_history", []),
    )
