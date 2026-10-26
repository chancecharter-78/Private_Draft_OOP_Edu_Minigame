
import psycopg

from Repository.database import open_player_database


def create_player(
    username_key,
    display_name,
    salt_hex,
    hash_hex,
    starter_csv,
    default_server_name,
):
    try:
        with open_player_database() as connection:
            connection.execute(
                """
                INSERT INTO players (username_key, username, password_salt, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (username_key, display_name, salt_hex, hash_hex),
            )
            cursor = connection.execute(
                """
                INSERT INTO question_sets (username_key, name, csv_text)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (username_key, "Starter questions", starter_csv),
            )
            set_id = cursor.fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO servers (username_key, name, is_default)
                VALUES (%s, %s, TRUE)
                RETURNING id
                """,
                (username_key, default_server_name),
            )
            default_server_id = cursor.fetchone()[0]
            connection.execute(
                """
                INSERT INTO server_question_sets
                    (username_key, server_id, question_set_id)
                VALUES (%s, %s, %s)
                """,
                (username_key, default_server_id, set_id),
            )
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO servers (username_key, name)
                    VALUES (%s, %s)
                    """,
                    [
                        (username_key, "Server 2"),
                        (username_key, "Server 3"),
                    ],
                )
            connection.execute(
                "UPDATE players SET active_question_set = %s WHERE username_key = %s",
                (set_id, username_key),
            )
    except psycopg.errors.UniqueViolation:
        return False
    return True


def get_credentials(username_key):
    with open_player_database() as connection:
        return connection.execute(
            """
            SELECT username, password_salt, password_hash, score, completed_rounds
            FROM players
            WHERE username_key = %s
            """,
            (username_key,),
        ).fetchone()


def get_clear_history(username_key):
    with open_player_database() as connection:
        return connection.execute(
            """
            SELECT game, level, points, details
            FROM player_clears
            WHERE username_key = %s
            ORDER BY id
            """,
            (username_key,),
        ).fetchall()


def add_score(username_key, amount):
    with open_player_database() as connection:
        cursor = connection.execute(
            "UPDATE players SET score = score + %s WHERE username_key = %s",
            (amount, username_key),
        )
        if cursor.rowcount != 1:
            return None
        return connection.execute(
            "SELECT score FROM players WHERE username_key = %s",
            (username_key,),
        ).fetchone()[0]


def insert_clear(username_key, game_name, level_cleared, points, details):
    with open_player_database() as connection:
        cursor = connection.execute(
            """
            UPDATE players
            SET score = score + %s, completed_rounds = completed_rounds + 1
            WHERE username_key = %s
            """,
            (points, username_key),
        )
        if cursor.rowcount != 1:
            return None
        connection.execute(
            """
            INSERT INTO player_clears (username_key, game, level, points, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username_key, game_name, level_cleared, points, details),
        )
        return connection.execute(
            """
            SELECT score, completed_rounds
            FROM players
            WHERE username_key = %s
            """,
            (username_key,),
        ).fetchone()


def reset_progress(username_key):
    with open_player_database() as connection:
        cursor = connection.execute(
            """
            UPDATE players
            SET score = 0, completed_rounds = 0
            WHERE username_key = %s
            """,
            (username_key,),
        )
        if cursor.rowcount != 1:
            return False
        connection.execute(
            "DELETE FROM player_clears WHERE username_key = %s",
            (username_key,),
        )
    return True


def get_leaderboard_rows(limit):
    with open_player_database() as connection:
        return connection.execute(
            """
            SELECT username, score, completed_rounds
            FROM players
            ORDER BY score DESC, completed_rounds DESC, lower(username)
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
