
import json

from Repository.database import open_player_database, review_schema_guard


def _default_server_id(connection, username_key):
    row = connection.execute(
        """
        SELECT id FROM servers
        WHERE username_key = %s AND is_default
        """,
        (username_key,),
    ).fetchone()
    if row is None:
        raise ValueError("This player does not have a default server.")
    return row[0]


def get_review_cards(username_key, server_id=None):
    with review_schema_guard():
        with open_player_database() as connection:
            if server_id is None:
                server_id = _default_server_id(connection, username_key)
            rows = connection.execute(
                """
                SELECT question_set_id, question_key, card_json
                FROM question_review_cards
                WHERE username_key = %s AND server_id = %s
                """,
                (username_key, server_id),
            ).fetchall()
    return {
        (question_set_id, question_key): json.loads(card_json)
        for question_set_id, question_key, card_json in rows
    }


def update_review_card(
    username_key,
    server_id,
    question_set_id,
    question_key,
    update_card,
):
    with review_schema_guard():
        with open_player_database() as connection:
            if server_id is None:
                server_id = _default_server_id(connection, username_key)
            if question_set_id is None:
                selected = connection.execute(
                    """
                    SELECT question_set_id FROM server_question_sets
                    WHERE username_key = %s AND server_id = %s
                    ORDER BY question_set_id
                    LIMIT 1
                    """,
                    (username_key, server_id),
                ).fetchone()
                if selected is None:
                    raise ValueError(
                        "This server does not have any question sets selected."
                    )
                question_set_id = selected[0]
            row = connection.execute(
                """
                SELECT card_json FROM question_review_cards
                WHERE username_key = %s AND server_id = %s
                    AND question_set_id = %s AND question_key = %s
                """,
                (username_key, server_id, question_set_id, question_key),
            ).fetchone()
            current_card = json.loads(row[0]) if row else None
            next_card = update_card(current_card)
            connection.execute(
                """
                INSERT INTO question_review_cards
                    (username_key, server_id, question_set_id, question_key, card_json)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username_key, server_id, question_set_id, question_key)
                DO UPDATE SET card_json = excluded.card_json
                """,
                (
                    username_key,
                    server_id,
                    question_set_id,
                    question_key,
                    json.dumps(next_card),
                ),
            )
    return next_card
