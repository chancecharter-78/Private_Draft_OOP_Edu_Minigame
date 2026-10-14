"""Database connection configuration and shared persistence exceptions."""

import os
from contextlib import contextmanager

import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


class QuestionReviewSchemaError(RuntimeError):
    """Raised when the database is missing the question-review migration."""


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
