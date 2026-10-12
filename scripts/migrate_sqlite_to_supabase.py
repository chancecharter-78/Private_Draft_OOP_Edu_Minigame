import argparse
import os
import sqlite3
from pathlib import Path

import psycopg


PLAYER_COLUMNS = (
    "username_key",
    "username",
    "password_salt",
    "password_hash",
    "score",
    "level",
    "completed_rounds",
    "active_question_set",
)
QUESTION_SET_COLUMNS = ("id", "username_key", "name", "csv_text")
CLEAR_COLUMNS = ("id", "username_key", "game", "level", "points", "details")


def read_table(connection, table_name, columns, defaults):
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if table_name not in tables:
        return []

    available_columns = {
        row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")
    }
    selected_columns = [column for column in columns if column in available_columns]
    rows = connection.execute(
        f"SELECT {', '.join(selected_columns)} FROM {table_name}"
    ).fetchall()
    return [
        {
            column: row[column] if column in selected_columns else defaults.get(column)
            for column in columns
        }
        for row in rows
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Copy a local player SQLite database into Supabase PostgreSQL."
    )
    parser.add_argument(
        "sqlite_path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "nierva_players.sqlite3",
    )
    args = parser.parse_args()
    if not args.sqlite_path.is_file():
        parser.error(f"SQLite database not found: {args.sqlite_path}")

    database_url = os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        parser.error("Set SUPABASE_DB_URL to the Supabase PostgreSQL connection URI.")

    with sqlite3.connect(args.sqlite_path) as source:
        source.row_factory = sqlite3.Row
        players = read_table(
            source,
            "players",
            PLAYER_COLUMNS,
            {
                "password_salt": "",
                "password_hash": "",
                "score": 0,
                "level": 1,
                "completed_rounds": 0,
                "active_question_set": None,
            },
        )
        question_sets = read_table(
            source, "question_sets", QUESTION_SET_COLUMNS, {}
        )
        clears = read_table(source, "player_clears", CLEAR_COLUMNS, {"details": ""})

    with psycopg.connect(database_url, connect_timeout=10) as destination:
        has_existing_players = destination.execute(
            "SELECT EXISTS (SELECT 1 FROM players)"
        ).fetchone()[0]
        if has_existing_players:
            raise RuntimeError(
                "Supabase already contains players; refusing to import and risk "
                "overwriting live data."
            )

        destination.executemany(
            """
            INSERT INTO players (
                username_key, username, password_salt, password_hash, score,
                level, completed_rounds, active_question_set
            ) VALUES (
                %(username_key)s, %(username)s, %(password_salt)s,
                %(password_hash)s, %(score)s, %(level)s, %(completed_rounds)s,
                %(active_question_set)s
            )
            """,
            players,
        )
        destination.executemany(
            """
            INSERT INTO question_sets (id, username_key, name, csv_text)
            VALUES (%(id)s, %(username_key)s, %(name)s, %(csv_text)s)
            """,
            question_sets,
        )
        destination.executemany(
            """
            INSERT INTO player_clears (id, username_key, game, level, points, details)
            VALUES (%(id)s, %(username_key)s, %(game)s, %(level)s, %(points)s, %(details)s)
            """,
            clears,
        )
        for table_name in ("question_sets", "player_clears"):
            destination.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence(%s, 'id'),
                    COALESCE((SELECT MAX(id) FROM {}), 1),
                    EXISTS (SELECT 1 FROM {})
                )
                """.format(table_name),
                (table_name,),
            )

    print(
        f"Imported {len(players)} players, {len(question_sets)} question sets, "
        f"and {len(clears)} game clears."
    )


if __name__ == "__main__":
    main()
