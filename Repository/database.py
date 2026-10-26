
import os
from contextlib import contextmanager

import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


QUESTION_REVIEW_MIGRATION_MESSAGE = (
    "Server and question review tables are not set up in the database. Run "
    "the Supabase migrations, including "
    "supabase/migrations/20261018000000_create_servers.sql, then retry."
)


class QuestionReviewSchemaError(RuntimeError):
    pass

class DuplicateNameError(Exception):
    pass

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


@contextmanager
def review_schema_guard():
    try:
        yield
    except (
        psycopg.errors.UndefinedTable,
        psycopg.errors.UndefinedColumn,
    ) as error:
        raise QuestionReviewSchemaError(
            QUESTION_REVIEW_MIGRATION_MESSAGE
        ) from error
