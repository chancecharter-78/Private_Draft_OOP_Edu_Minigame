import streamlit as st

import nierva_about
import nierva_bit_fit
import nierva_csvdb
import nierva_hacking
import nierva_home
import nierva_leaderboard
import nierva_progression
import nierva_slider
import nierva_source
from nierva_save_data import (
    authenticate_player,
    clean_username,
    register_player,
)


GAME_PAGES = {
    "Slider": nierva_slider.main,
    "Bit Fit": nierva_bit_fit.main,
    "Hacking": nierva_hacking.main,
}
INFO_PAGES = {
    "Homepage": nierva_home.main,
    "About me": nierva_about.main,
    "Source": nierva_source.main,
    "Leaderboard": nierva_leaderboard.main,
    "Question Sets": nierva_csvdb.main,
}


def init():
    st.session_state.setdefault("page", "Homepage")
    st.session_state.setdefault("project", False)
    st.session_state.setdefault("game", False)
    st.session_state.setdefault("switch_message", "")
    if "username" in st.session_state and "save_data" not in st.session_state:
        del st.session_state["username"]


def draw_style():
    st.set_page_config(
        page_title="Educational Minigames Prototype",
        page_icon="🎮",
        layout="centered",
    )
    st.markdown(
        """
        <style>
            header {visibility: visible;}
            footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sign_in():
    st.title("Welcome to the Educational Minigames Prototype")
    st.caption("Create an account or sign in to save your local game progress.")

    create_tab, login_tab = st.tabs(["Create account", "Sign in"])
    with create_tab:
        with st.form("new_player"):
            st.text_input("Username", key="new_username", max_chars=20)
            st.text_input(
                "Password (at least 8 characters)",
                type="password",
                key="new_password",
                max_chars=128,
            )
            st.form_submit_button("Create account", on_click=create_account)

    with login_tab:
        with st.form("returning_player"):
            st.text_input("Username", key="login_username", max_chars=20)
            st.text_input(
                "Password",
                type="password",
                key="login_password",
                max_chars=128,
            )
            st.form_submit_button("Sign in", on_click=log_in)

    if st.session_state.get("auth_error"):
        st.error(st.session_state.auth_error)


def create_account():
    try:
        username = clean_username(st.session_state.new_username)
        save_data, message = register_player(
            username,
            st.session_state.new_password,
        )
        st.session_state.new_password = ""
        if save_data is None:
            st.session_state.auth_error = message
            return
        start_session(username, save_data)
    except ValueError as error:
        st.session_state.new_password = ""
        st.session_state.auth_error = str(error)


def log_in():
    save_data = authenticate_player(
        st.session_state.login_username,
        st.session_state.login_password,
    )
    st.session_state.login_password = ""
    if save_data is None:
        st.session_state.auth_error = "Username or password is incorrect."
        return
    start_session(save_data.player_name, save_data)


def start_session(username, save_data):
    st.session_state["new_password"] = ""
    st.session_state["login_password"] = ""
    st.session_state.username = username
    st.session_state.save_data = save_data
    st.session_state.page = "Homepage"
    st.session_state.auth_error = ""


def sign_out():
    st.session_state.clear()


def set_page(page):
    if page in GAME_PAGES:
        nierva_progression.start_game(page)
        return
    st.session_state.page = page


def start_minigames():
    current_game = st.session_state.get("flow_game")
    if current_game in GAME_PAGES:
        st.session_state.page = current_game
        st.session_state.project = True
        st.session_state.game = True
    else:
        nierva_progression.start_game("Slider")


def select_game():
    nierva_progression.start_game(st.session_state.nav_game)


def load_page():
    page = st.session_state.get("page", "Homepage")
    if page in GAME_PAGES:
        GAME_PAGES[page]()
    else:
        INFO_PAGES.get(page, nierva_home.main)()


def main():
    draw_style()
    init()

    if "username" not in st.session_state:
        sign_in()
        return

    with st.sidebar:
        if st.session_state.get("game", False):
            st.selectbox(
                "Select Minigame Prototype",
                nierva_progression.GAME_ORDER,
                key="nav_game",
                index=nierva_progression.GAME_ORDER.index(
                    st.session_state.get("flow_game", "Slider")
                ),
                on_change=select_game,
            )

        if st.session_state.page in GAME_PAGES:
            st.button(
                "🏠 Homepage",
                on_click=set_page,
                args=("Homepage",),
                width="stretch",
            )
        else:
            st.button(
                "📌 Minigames",
                on_click=start_minigames,
                width="stretch",
            )

        about_col, source_col = st.columns(2)
        about_col.button(
            "🧑‍💻 Myself",
            on_click=set_page,
            args=("About me",),
            width="stretch",
        )
        source_col.button(
            "📁 Source",
            on_click=set_page,
            args=("Source",),
            width="stretch",
        )
        st.button(
            "🏆 Leaderboard",
            on_click=set_page,
            args=("Leaderboard",),
            width="stretch",
        )
        st.button(
            "📚 Question Sets",
            on_click=set_page,
            args=("Question Sets",),
            width="stretch",
        )
        st.button(
            "Sign out",
            on_click=sign_out,
            width="stretch",
        )

    load_page()

    message = st.session_state.get("switch_message", "")
    if message:
        st.success(message)
        st.session_state.switch_message = ""


if __name__ == "__main__":
    main()
