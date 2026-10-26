
import psycopg
import streamlit as st

from Controller import navigation
from Repository.database import QuestionReviewSchemaError
from View import (
    about,
    account,
    home,
    leaderboard,
    minigame,
    navigation as navigation_view,
    question_sets,
    servers,
    source,
)

GAME_PAGES = {
    "Slider": minigame.render_slider_page,
    "Bit Fit": minigame.render_bit_fit_page,
    "Hacking": minigame.render_hacking_page,
}
INFO_PAGES = {
    "Homepage": home.main,
    "Servers": servers.main,
    "Server menu": servers.main,
    "About me": about.main,
    "Source": source.main,
    "Leaderboard": leaderboard.main,
    "Question Sets": question_sets.main,
}


def load_page():
    page = navigation.current_page()
    if page in GAME_PAGES:
        GAME_PAGES[page]()
    else:
        INFO_PAGES.get(page, home.main)()


def main():
    navigation_view.draw_style()
    navigation.init_session()

    if "username" not in st.session_state:
        account.sign_in()
        return

    navigation_view.render_sidebar()

    if st.session_state.get("sign_out_confirmation_open", False):
        account.confirm_sign_out()

    try:
        load_page()
    except QuestionReviewSchemaError as error:
        st.error(str(error))
    except psycopg.Error as error:
        st.error(navigation.format_database_error(error))


if __name__ == "__main__":
    main()
