
import json

import psycopg

from Repository.database import DuplicateNameError, open_player_database


def _fetch_server_data(connection, username_key, server_id):
    question_sets = connection.execute(
        """
        SELECT server_question_sets.question_set_id, question_sets.csv_text
        FROM server_question_sets
        JOIN question_sets
            ON question_sets.username_key = server_question_sets.username_key
            AND question_sets.id = server_question_sets.question_set_id
        WHERE server_question_sets.username_key = %s
            AND server_question_sets.server_id = %s
        ORDER BY server_question_sets.question_set_id
        """,
        (username_key, server_id),
    ).fetchall()
    question_set_ids = [question_set_id for question_set_id, _ in question_sets]
    if not question_set_ids:
        return [], {}

    cards = connection.execute(
        """
        SELECT question_set_id, question_key, card_json
        FROM question_review_cards
        WHERE username_key = %s AND server_id = %s
            AND question_set_id = ANY(%s)
        """,
        (username_key, server_id, question_set_ids),
    ).fetchall()
    review_cards = {
        (question_set_id, question_key): json.loads(card_json)
        for question_set_id, question_key, card_json in cards
    }
    return question_sets, review_cards


def fetch_server_overview(username_key):
    with open_player_database() as connection:
        rows = connection.execute(
            """
            SELECT id, name, is_default
            FROM servers
            WHERE servers.username_key = %s
            ORDER BY servers.id
            """,
            (username_key,),
        ).fetchall()
        overview = []
        for server_id, name, is_default in rows:
            question_sets, review_cards = _fetch_server_data(
                connection,
                username_key,
                server_id,
            )
            overview.append({
                "id": server_id,
                "name": name,
                "is_default": is_default,
                "question_sets": question_sets,
                "review_cards": review_cards,
            })
    return overview


def fetch_server_review_data(username_key, server_id):
    with open_player_database() as connection:
        return _fetch_server_data(connection, username_key, server_id)


def insert_next_server(username_key, choose_name):
    with open_player_database() as connection:
        names = {
            name
            for (name,) in connection.execute(
                "SELECT name FROM servers WHERE username_key = %s",
                (username_key,),
            ).fetchall()
        }
        cursor = connection.execute(
            """
            INSERT INTO servers (username_key, name)
            VALUES (%s, %s)
            RETURNING id, name
            """,
            (username_key, choose_name(names)),
        )
        return cursor.fetchone()


def rename_server(username_key, server_id, name):
    try:
        with open_player_database() as connection:
            cursor = connection.execute(
                """
                UPDATE servers SET name = %s
                WHERE username_key = %s AND id = %s
                """,
                (name, username_key, server_id),
            )
    except psycopg.errors.UniqueViolation as error:
        raise DuplicateNameError(name) from error
    return cursor.rowcount == 1


def get_server_question_set_ids(username_key, server_id):
    with open_player_database() as connection:
        rows = connection.execute(
            """
            SELECT question_set_id FROM server_question_sets
            WHERE username_key = %s AND server_id = %s
            ORDER BY question_set_id
            """,
            (username_key, server_id),
        ).fetchall()
    return [question_set_id for (question_set_id,) in rows]


def replace_server_question_sets(username_key, server_id, selected_ids):
    with open_player_database() as connection:
        server = connection.execute(
            "SELECT 1 FROM servers WHERE username_key = %s AND id = %s",
            (username_key, server_id),
        ).fetchone()
        if server is None:
            return False
        if selected_ids:
            rows = connection.execute(
                """
                SELECT id FROM question_sets
                WHERE username_key = %s AND id = ANY(%s)
                """,
                (username_key, selected_ids),
            ).fetchall()
            if len(rows) != len(selected_ids):
                raise ValueError(
                    "One or more selected question sets are unavailable to this account."
                )

        connection.execute(
            """
            DELETE FROM server_question_sets
            WHERE username_key = %s AND server_id = %s
            """,
            (username_key, server_id),
        )
        if selected_ids:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO server_question_sets
                        (username_key, server_id, question_set_id)
                    VALUES (%s, %s, %s)
                    """,
                    [(username_key, server_id, set_id) for set_id in selected_ids],
                )
    return True


def delete_server(username_key, server_id):
    with open_player_database() as connection:
        cursor = connection.execute(
            "DELETE FROM servers WHERE username_key = %s AND id = %s",
            (username_key, server_id),
        )
    return cursor.rowcount == 1
