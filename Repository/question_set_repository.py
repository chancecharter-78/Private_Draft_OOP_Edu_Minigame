
from pathlib import Path

import psycopg

from Repository.database import DuplicateNameError, open_player_database


STARTER_QUESTIONS_PATH = (
    Path(__file__).resolve().parent.parent / "nierva_questions.csv"
)


def load_starter_csv():
    return STARTER_QUESTIONS_PATH.read_text(encoding="utf-8-sig")


def list_question_sets(username_key):
    with open_player_database() as connection:
        return connection.execute(
            """
            SELECT question_sets.id, question_sets.name,
                question_sets.id = players.active_question_set
            FROM question_sets
            JOIN players USING (username_key)
            WHERE question_sets.username_key = %s
            ORDER BY lower(question_sets.name)
            """,
            (username_key,),
        ).fetchall()


def get_question_set_csv(username_key, set_id=None):
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
                (username_key, username_key),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT csv_text FROM question_sets
                WHERE username_key = %s AND id = %s
                """,
                (username_key, set_id),
            ).fetchone()
    return None if row is None else row[0]


def insert_question_set(username_key, name, csv_text):
    try:
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                INSERT INTO question_sets (username_key, name, csv_text)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (username_key, name, csv_text),
            )
            return cursor.fetchone()[0]
    except psycopg.errors.UniqueViolation as error:
        raise DuplicateNameError(name) from error


def update_question_set(username_key, set_id, name, csv_text):
    try:
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                UPDATE question_sets
                SET name = %s, csv_text = %s
                WHERE username_key = %s AND id = %s
                """,
                (name, csv_text, username_key, set_id),
            )
    except psycopg.errors.UniqueViolation as error:
        raise DuplicateNameError(name) from error
    return cursor.rowcount == 1


def set_active_question_set(username_key, set_id):
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
            (set_id, username_key, set_id, username_key),
        )
    return cursor.rowcount == 1


def delete_question_set(username_key, set_id):
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
            (set_id, username_key, username_key),
        )
    return cursor.rowcount == 1


def get_server_question_sets(username_key, server_id=None):
    with open_player_database() as connection:
        if server_id is None:
            server = connection.execute(
                """
                SELECT id FROM servers
                WHERE username_key = %s AND is_default
                """,
                (username_key,),
            ).fetchone()
            if server is None:
                raise ValueError("This player does not have a default server.")
            server_id = server[0]
        rows = connection.execute(
            """
            SELECT question_sets.id, question_sets.csv_text
            FROM server_question_sets
            JOIN question_sets
                ON question_sets.id = server_question_sets.question_set_id
                AND question_sets.username_key = server_question_sets.username_key
            WHERE server_question_sets.username_key = %s
                AND server_question_sets.server_id = %s
            ORDER BY question_sets.id
            """,
            (username_key, server_id),
        ).fetchall()
    return server_id, rows
