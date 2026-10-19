
import psycopg
import streamlit as st

from Controller import minigame
from Model import game_flow


def init_session():
    st.session_state.setdefault("page", "Homepage")
    st.session_state.setdefault("project", False)
    st.session_state.setdefault("game", False)
    if "username" in st.session_state and "save_data" not in st.session_state:
        del st.session_state["username"]


def set_page(page, reset_game=False):
    if page in game_flow.GAME_ORDER:
        minigame.start_game(page)
        return

    st.session_state.page = page
    if reset_game:
        st.session_state.project = False
        st.session_state.game = False


def show_servers():
    set_page("Servers", reset_game=True)


def current_page():
    return st.session_state.get("page", "Homepage")


def format_database_error(error):
    if isinstance(error, psycopg.errors.UndefinedTable):
        return (
            "The configured database is missing a table required by the app. "
            "If this database already contains player or question-set data, do "
            "not rerun the initial schema setup; first verify that "
            "SUPABASE_DB_URL points to the existing project. Then apply any "
            "pending migrations listed in DEPLOYMENT.md, including the server "
            "migration. Run the initial schema setup only when creating a new, "
            "empty database."
        )
    return (
        "The database could not complete this action "
        f"({type(error).__name__}). Please retry. If it continues, contact "
        "the app administrator."
    )
